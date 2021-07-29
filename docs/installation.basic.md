# Installation
Karen is available as separate components that together create an extensible environment for devices and processing input/output.  These components can be installed together or separately depending on your needs.  This page attempts to articulate how to install each of the components and their dependencies.

## Install the BRAIN
In order for Karen to work properly you must have a running instance of ```kbrain```.  The brain is fairly straightforward to install with the following steps:

```
sudo apt-get install libfann2 python3-fann2 
```
```
pip3 install karen-brain
```

Then to start the brain you can run the following:
```
import karen
karen.start("/path/to/config.json")
```
Please make note that to start the brain by itself then you must specify your own configuration file as all of the built-in configurations will include a brain and device instance in their startup.

## Install the DEVICE CONTAINER
The device container service is used to allow the brain to interact with the input/output devices like a microphone or speaker output.  The individual device plugins can be installed separately.  To install the device container service follow the steps below:
```
pip3 install karen-device
```
Then to start the device service you can run the following:
```
import karen
karen.start("/path/to/config.json")
```
Please make note that to start the Device service by itself then you must specify your own configuration file as all of the built-in configurations will include a brain and device instance in their startup.  See more information in the [configuration overview](config.overview.md) on how to start a device container with a remote brain.

### Plugins: SPEAKER
The Speaker plugin allows Karen to send Text-to-Speech output to your audio output device.  To install the speaker follow the steps below:
```
sudo apt-get install festival festvox-us-slt-hts
```
```
pip3 install karen-device karen-plugin-speaker
```
See more details in the [configuration overview](config.overview.md) on how to include a speaker device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: LISTENER
The Listener plugin allows Karen to receive audio input and then process it via Speech-to-Text for further processing in the Brain module.  To install the listener follow the steps below:
```
sudo apt-get install libportaudio2 libasound2-dev
```
```
pip3 install karen-device karen-plugin-listener
```
The listener device installation does not automatically include the speech models althought it does include a method to allow you to download these.  To download the speech models after installation execute these steps in a python prompt or script:
```
import karen_listener
model_type = "pbmm"                         # use "tflite" for Raspberry Pi
karen_listener.download_models(model_type)  # Downloads models for deepspeech
```

See more details in the [configuration overview](config.overview.md) on how to include a listener device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: WATCHER
The Watcher plugin allows Karen to capture video and also process it for object detection and face recognition.  It then sends this information to the Brain for further processing.  To install the watcher follow the steps below:
```
sudo apt-get install libatlas-base-dev cmake
```
```
pip3 install karen-device karen-plugin-watcher
```
See more details in the [configuration overview](config.overview.md) on how to include a watcher device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: PANEL
Coming soon!
