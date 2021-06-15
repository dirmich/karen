# Project Karen &middot; [![GitHub license](https://img.shields.io/github/license/lnxusr1/karen)](https://github.com/lnxusr1/karen/blob/master/LICENSE) [![Python Versions](https://img.shields.io/pypi/pyversions/yt2mp3.svg)](https://github.com/lnxusr1/karen/)
This project is dedicated to building a "Synthetic Human" which is called Karen (for now) for which we have assigned the female gender pronoun of "She". She has visual face recognition ([opencv/opencv](https://github.com/opencv/opencv)), speech transcription ([mozilla/deepspeech](https://github.com/mozilla/DeepSpeech)), and speech synthesis ([festival](http://www.cstr.ed.ac.uk/projects/festival/)).  Karen is written in Python and is targeted primarily at the single board computer (SBC) platforms like the [Raspberry Pi](https://www.raspberrypi.org/).

## Installation
You will likely need a few extra packages and libraries to run Karen's core routines.  The details on all of this is available on our installation page at the link below.

[https://docs.projectkaren.ai/](https://docs.projectkaren.ai/)

### OS generation-specific libraries

```
# These libraries only apply to Ubuntu 18.04 and similar generations of Debian
sudo apt-get install libqtgui4 \
  libqt4-test

# These libraries only apply to Ubuntu 20.04
sudo apt-get install libqt5gui5 \
  libqt5test5
```

### Foundational required binaries and headers


```
# Required Libraries and Packages
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

### Required Python Libraries

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

### Mozilla DeepSpeech Models
To download the speech models you can use the script below or visit the [DeepSpeech](https://github.com/mozilla/DeepSpeech) page:

```
wget https://raw.githubusercontent.com/lnxusr1/karen/0ab615ead3862326d69926294267f0a8669886dd/models/speech/download-models.sh
sh ./download-models.sh
```

## Starting Up
There are lots of ways to leverage karen.  You can import the device modules like listener and use on its own or you can start the entire process.  Check out the "run.py" for some ideas on how to build a device container and add input/output devices to it.

To run Karen in the entirety:

```
python3 run.py [parameters]
```

To run Karen as a background process check out:

```
run.sh [parameters]
```

**NOTICE** - Karen is under development against Python 3.  She is not compatible with Python 2 so be sure to use "python3" or "python3" (and install the related binaries if needed).

## Project Goals
I'm not sure where we will end up but the goals for this project are pretty simple:

1. Must be able to do every day tasks (tell time, weather, and be context aware)
2. Must provide evidence of "thought" (I'm still working on what exactly this means)
3. Must be fun (because the moment it becomes "work" I'm sure we'll all lose interest)

## Help &amp; Support
Installation instructions and documentation is available at [https://projectkaren.ai](https://projectkaren.ai)

