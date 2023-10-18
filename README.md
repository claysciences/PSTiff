# PSTiff
Python tools to easily write layered tiff files in a format compatible with Adobe Photoshop
based on psdtags

```
from cspstiff import CSPSTiff
import imagecodecs

background = imagecodecs.imread("background.png")
annotation = imagecodecs.imread("annotation.png")
decoration = imagecodecs.imread("decoration.png")

tiffobj = CSPSTiff(background.shape[:2])
tiffobj.add_layer(background, name="background")
tiffobj.add_layer(annotation, name="annotation")
tiffobj.add_layer(decoration, (200,200), name="decoration 1")
tiffobj.add_layer(decoration, (300,400), name="decoration 2")

m.write("layered.tiff")
```
