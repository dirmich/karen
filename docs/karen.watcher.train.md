# Training your Watcher

Karen has built-in capacity for face detection.  This is done using the haarcascade classifiers in conjunction with openCV.

All three haarcascade classifiers are included in the installation package and available under "data/models/watcher".  The haarcascade_frontal_default.xml is used if no classifier is explicitly specified.

To train your model the train() method needs to be called.  The most simple method is:

```
import karen.watcher
watcher = Watcher()
watcher.train("/path/to/your/faces-directory")
```

Your faces directory should be configured as follows:

```
/faces-directory
   - /Jane
       - /image1.jpg
       - /image2.jpg
       - /image3.jpg
   - /John
       - /image1.jpg
       - /image2.jpg
       - /image3.jpg
```

This will create a ```recognizer.yml``` file and a ```names.json``` file.  These files are both used to determine who Karen sees when capturing video.  If you already have a recognizer and names file built you can specify them with the ```recognizerFile``` and ```namesFile``` parameters when creating a new Watcher device.  An example of these parameters is available in the [Basic Audio/Video Example](config.example.video.md)

For more details on the watcher check out the [Watcher class definition](karen.watcher.md)