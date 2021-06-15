# Installation
You will likely need a few extra packages and libraries to run Karen's core routines.  Check out the details below to jumpstart your Karen-experience.

## OS Specific Libraries

```
# These libraries only apply to Ubuntu 18.04 and similar generations of Debian
sudo apt-get install libqtgui4 \
  libqt4-test

# Ubuntu 20.04
sudo apt-get install libqt5gui5 \
  libqt5test5
```

## Required Binaries & Headers


```
sudo apt-get install python3-pip \
  python3-opencv \
  libatlas-base-dev \
  python3-pyqt5 \
  pulseaudio \
  pamix \
  pavucontrol \
  libpulse-dev \
  libportaudio2 \
  libasound2-dev \
  festival festvox-us-slt-hts  \
  libfann-dev \
  python3-dev \
  python3-pip \
  python3-fann2 \
  swig \
  portaudio19-dev \
  python3-pyaudio
```

## Required Python Libraries

```
sudo pip3 install opencv-python \
  opencv-contrib-python \
  pyaudio \
  Pillow \
  webrtcvad \
  halo \
  scipy \
  deepspeech \
  padatious
```

## Mozilla DeepSpeech Models
To download the speech models you can use the script below or visit the [DeepSpeech](https://github.com/mozilla/DeepSpeech) page:

```
wget https://raw.githubusercontent.com/lnxusr1/karen/0ab615ead3862326d69926294267f0a8669886dd/models/speech/download-models.sh
sh ./download-models.sh
```

## Starting Up
There are lots of ways to leverage karen.  You can import the device modules like listener and use on its own or you can start the entire process.  Check out the "run.py" for some ideas on how to build a device container and add input/output devices to it.  There is a basic configuration file located in the root of the code repository.

To run Karen in the entirety:

```
python3 run.py --config /path/to/base_config.json
```

To run Karen as a background process check out:

```
run.sh --config /path/to/base_config.json
```

**NOTICE** - Karen is under development against Python 3.  She is not compatible with Python 2 so be sure to use "python3" or "python3" (and install the related binaries if needed).

## Help &amp; Support
Installation instructions and documentation is available at [https://projectkaren.ai](https://projectkaren.ai)

