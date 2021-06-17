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

### Install with PIP (Recommended)

```
pip3 install karen
```

**NOTICE** - Karen is under development against Python 3.  She is not compatible with Python 2 so be sure to use ```pip3``` or ```python3``` if appropriate (and install the related binaries if needed).

### Install via Download (Alternative)

Make sure you see the requirements.txt for other python libraries that are required.  The PIP method is recommended as it will automatically include these dependencies.

```
cd /path/to/karen
python3 setup.py install
```

### Get the Mozilla DeepSpeech Models
To download the speech models you can use the script below inside a Python shell or visit the [DeepSpeech](https://github.com/mozilla/DeepSpeech/releases/latest) page:

```
import karen
karen.download_models(version="0.9.3", model_type="pbmm", include_scorer=True)
```

__NOTE:__  The version number is optional and if ommitted the process will attempt to determine your currently installed version of deepspeech.  Also, you will need to specify ```model_type="tflite"``` if you are running on Raspberry Pi as the pbmm models are not compatible with the Arm architecture.


* Once you're finished make sure to read about __[Starting Up](karen.md)__.

-----

## Help &amp; Support
Installation instructions and documentation is available at [https://projectkaren.ai](https://projectkaren.ai)

