from collections import OrderedDict

import imagecodecs
import tifffile
import numpy as np
from psdtags import (
    __version__,
    PsdBlendMode,
    PsdChannel,
    PsdChannelId,
    PsdClippingType,
    PsdColorSpaceType,
    PsdCompressionType,
    PsdEmpty,
    PsdFilterMask,
    PsdFormat,
    PsdKey,
    PsdLayer,
    PsdLayerFlag,
    PsdLayerMask,
    PsdLayers,
    PsdRectangle,
    PsdString,
    PsdUserMask,
    TiffImageSourceData,
    overlay,
)

TIFFIMAGESOURCEDATA_PARAMS_DICT = OrderedDict(
    name='Layered TIFF',
    psdformat=PsdFormat.LE32BIT,
    layers=None,
    usermask=PsdUserMask(
        colorspace=PsdColorSpaceType.RGB,
        components=(65535, 0, 0, 0),
        opacity=50,
    ),
    info=[
        PsdEmpty(PsdKey.PATTERNS),
        PsdFilterMask(
            colorspace=PsdColorSpaceType.RGB,
            components=(65535, 0, 0, 0),
            opacity=50,
        ),
    ],
)


class CSPSTiff:
    def __init__(self, shape=None):
        """
        Initialize the object. 
        shape: 2-tuple. If None, shape will be taken from the first layer.
        """
        self.shape = shape
        self.layers = []


    def add_layer(self, img, offset=(0,0)):
        """
            img - ndarray image data. if RGB, convert to RGBA by adding transparency layer at 50%
            offset - in pixels from (top, left), defaults to (0,0)

        """
        
        if img.shape[2] == 3:
            print("IMG HAS ONLY 3 CHANNELS (should be RGBA)")
            rgba_image = np.zeros((img.shape[0], img.shape[1], 4), dtype=np.uint8)
            rgba_image[:, :, :3] = img
            alpha_value = 128  # set it to 128 for a semi-transparent image
            rgba_image[:, :, 3] = alpha_value
            img = rgba_image

        # if self.shape is not set yet, take it from first layer
        if self.shape is None:
            self.shape = img.shape[:2]
        elif img.shape[:2] != self.shape:
            print(f"IMG shape is {img.shape[:2]}, existing shape is {self.shape}")

        self.layers.append((img, offset))


    def _prep_layers(self):
        """
        Converts self.layers into a layers component that can feed into TiffImageSourceData
        """
        layers = []
        layer_num = 0
        for layer, offset in self.layers:
            layer_name = f"layer_{layer_num}"
            new_layer = PsdLayer(
                name = layer_name,
                rectangle=PsdRectangle(
                    offset[0], 
                    offset[1],
                    offset[0] + layer.shape[0],
                    offset[1] + layer.shape[1],
                ),
                channels=[
                       PsdChannel(
                        channelid=PsdChannelId.TRANSPARENCY_MASK,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=layer[..., 3],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL0,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=layer[..., 0],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL1,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=layer[..., 1],
                    ),
                    PsdChannel(
                        channelid=PsdChannelId.CHANNEL2,
                        compression=PsdCompressionType.ZIP_PREDICTED,
                        data=layer[..., 2],
                    ),
                ],
                mask=PsdLayerMask(),
                opacity=255,
                blendmode=PsdBlendMode.NORMAL,
                blending_ranges=(),
                clipping=PsdClippingType.BASE,
                flags=PsdLayerFlag.PHOTOSHOP5 | PsdLayerFlag.TRANSPARENCY_PROTECTED,
                info=[PsdString(PsdKey.UNICODE_LAYER_NAME, layer_name),]
                ,
            )
            layers.append(new_layer)
            layer_num += 1
            
        return layers

    def write(self, filepath:str):
        """
        Prepare a PhotoShop Tiff file from the layers provided and write to filepath
        """

        if len(self.layers) == 0:
            raise Exception("not enough layers")


        ll = PsdLayers(
            key=PsdKey.LAYER,
            has_transparency=False,
            layers=self._prep_layers())
        
        TIFFIMAGESOURCEDATA_PARAMS_DICT["layers"] = ll

        image_source_data = TiffImageSourceData(**TIFFIMAGESOURCEDATA_PARAMS_DICT)

        composite = overlay(*self.layers, shape=self.shape)

        tifffile.imwrite(
                            filepath, 
                            composite, 
                            photometric='rgb',
                            compression='adobe_deflate',
                            # 72 dpi resolutionֵ
                            resolution=((720000, 10000), (720000, 10000)),
                            resolutionunit='inch',
                            # do not write tifffile specific metadata
                            metadata=None,
                            # write layers and sRGB profile as extra tags
                            extratags=[
                            # ImageSourceData tag
                            image_source_data.tifftag(),
                                # InterColorProfile tag
                                (34675, 7, None, imagecodecs.cms_profile('srgb'), True),
                            ],
                        )
        # remove the layers component, reverting the change
        TIFFIMAGESOURCEDATA_PARAMS_DICT["layers"] = None
        

