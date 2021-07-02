# Calling the start() method
There are lots of ways to leverage karen.  You can import the device modules like listener and use on its own or you can start the entire process.  There is a [basic configuration](config.example.md) file located in the data directory inside the karen module directory (```/path/to/karen/data/basic_config.json```).

You will need to either download the speech models or reference them in the configuration file.  You can download the models with the following:

```
import karen
karen.download_models(model_type="pbmm", overwrite=False)
```

__ALERT:__ You should replace ```"pbmm"``` with ```"tflite"``` in the above command if you are downloading on the Raspberry Pi as Mozilla DeepSpeech only supports TensorFlow Lite on that platform.  

This method will attempt to download the deepspeech models if they don't already exist.  If they do exist then the command will exit having done nothing but verify the files exist.

# Listener + Speaker Example

To run Karen with just the Listener and Speaker enabled try the following:

```
import karen
karen.start()
```

This will start Karen with the [Basic Audio Example](config.example.md).  

# Listener + Speaker + Watcher Example

To run Karen with just the all the built-in devices enabled try the following:

```
import karen
karen.start("video")
```

This will start Karen with the [Basic Audio+Video Example](config.example.video.md).  You may also want to [train your model](karen.watcher.train.md) to recognize specific faces.

# Starting with a custom configuration

To run Karen with your own custom configuration:

```
import karen
karen.start("/path/to/your/config.json")
```

Karen's configuration file is pretty advanced so make sure you read the [Configuration Overview](config.overview.md).  

**NOTICE** - Karen is under development against Python 3.  She is not compatible with Python 2 so be sure to use ```pip3``` or ```python3``` if appropriate (and install the related binaries if needed).

-----

# karen.start

::: karen.start
    rendering:
      show_source: false