# Installation
Karen is available as separate components that together create an extensible environment for devices and the processing of input/output.  These components can be installed together or separately depending on your needs.  This page attempts to articulate how to install each of the components and their dependencies.

You may want to install Karen in a virtual python environment.  If so and you plan to use the PyQt5 libraries then we highly recommend including system-site-packages in your virtual environment.  This is due to a limitation in PyQt5 that requires manual installation if you don't include the pre-built packages in Linux (```apt-get install python3-pyqt5```).

To create a virtual environment try the following:

```
sudo apt-get install python3-venv
python3 -m venv /path/to/virtual/environment --system-site-packages
```

Then just use the binaries in the new virtual environment for the rest of the python package installations.

__NOTE:__ When Karen runs the program is configured to save its configuration and model files to the folder ```~/.karen/```.  This may be handy for troubleshooting.

## Install the BRAIN
In order for Karen to work properly you must have a running instance of ```karen_brain.Brain()```.  The brain is fairly straightforward to install with the following steps:

```
sudo apt-get install libfann2 python3-fann2 
```

```
pip3 install karen-brain
```
__NOTE:__ If you get an error on "Cannot find FANN libs" then please see the [Raspberry Pi instructions](installation.raspberrypi.md).

Then to start the brain you can run one of the following:

__As a module:__
```
python3 -m karen.run --config /path/to/config.json
```

__As code:__
```
import karen
karen.start("/path/to/config.json")
```

Please make note that to start the brain by itself then you must specify your own configuration file as all of the built-in configurations will include a brain and device container instance in their startup.

## Install the DEVICE CONTAINER
The device container service is used to allow the brain to interact with the input/output devices like a microphone or speaker output.  The individual device plugins can be installed separately.  To install the device container service follow the steps below:

```
pip3 install karen-device
```

Then to start the device service you can run one of the following:

__As a module:__
```
python3 -m karen.run --config /path/to/config.json
```

__As code:__
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

```
import karen_device, karen_speaker

brain_url = "http://localhost:8080"
device = karen_device.DeviceContainer(brain_url=brain_url)
speaker = karen_speaker.Speaker(callback=device.callbackHandler)
device.addDevice("karen_speaker.Speaker", speaker, autoStart=True)
device.start()
device.wait()
```

See more details in the [configuration overview](config.overview.md) on how to include a speaker device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: LISTENER
The Listener plugin allows Karen to receive audio input and then process it via Speech-to-Text for further processing in the Brain module.  To install the listener follow the steps below:

```
sudo apt-get install libportaudio2 libasound2-dev python3-dev
```

```
pip3 install karen-device karen-plugin-listener
```

The listener device installation does not automatically include the speech models although it does include a method to enable you to download them.  To download the speech models after installation execute these steps in a python prompt or script:

```
import karen_listener
model_type = "pbmm"                         # use "tflite" for Raspberry Pi
karen_listener.download_models(model_type)  # Downloads models for deepspeech
```

```
import karen_device, karen_listener

brain_url = "http://localhost:8080"
device = karen_device.DeviceContainer(brain_url=brain_url)
listener = karen_listener.Listener(callback=device.callbackHandler)
device.addDevice("karen_listener.Listener", listener, autoStart=True)
device.start()
device.wait()
```

See more details in the [configuration overview](config.overview.md) on how to include a listener device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: WATCHER
The Watcher plugin allows Karen to capture video and also process it for object detection and face recognition.  It then sends this information to the Brain for further processing.  To install the watcher follow the steps below:

```
sudo apt-get install libatlas-base-dev cmake
```

```
pip3 install scikit-build # includes skbuild for compiling opencv
pip3 install karen-device karen-plugin-watcher
```

```
import karen_device, karen_watcher

brain_url = "http://localhost:8080"
device = karen_device.DeviceContainer(brain_url=brain_url)
watcher = karen_watcher.Watcher(callback=device.callbackHandler)
device.addDevice("karen_watcher.Watcher", watcher, autoStart=True)
device.start()
device.wait()
```

See more details in the [configuration overview](config.overview.md) on how to include a watcher device in your device container configuration.  It will then be started with the Device Container in which it is included.

### Plugins: PANEL
The Panel plugin allows Karen to display items on a screen and accept touchscreen input. It interacts with the Brain to both control and consume inputs for displaying. To install the panel follow the steps below:

```
sudo apt-get install python3-pyqt5
```

```
pip3 install karen-device karen-plugin-panel
```

```
import karen_device, karen_panel

brain_url = "http://localhost:8080"
device = karen_device.DeviceContainer(brain_url=brain_url)
panel = karen_panel.Panel(callback=device.callbackHandler)
device.addDevice("karen_panel.Panel", panel, autoStart=True)
device.start()
device.wait()
```

See more details in the [configuration overview](config.overview.md) on how to include a panel device in your device container configuration.  It will then be started with the Device Container in which it is included.
