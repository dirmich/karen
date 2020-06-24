# Project Karen &middot; [![GitHub license](https://img.shields.io/github/license/lnxusr1/karen)](https://github.com/lnxusr1/karen/blob/master/LICENSE.md) [![Python Versions](https://img.shields.io/pypi/pyversions/yt2mp3.svg)](https://github.com/lnxusr1/karen/)
This project is dedicated to building a "Synthetic Human" which is called Karen (for now) for which we have assigned the female gender pronoun of "She". She has visual face recognition ([opencv/opencv](https://github.com/opencv/opencv)), speech transcription ([mozilla/deepspeech](https://github.com/mozilla/DeepSpeech)), and speech synthesis ([festival](http://www.cstr.ed.ac.uk/projects/festival/)).  Karen is written in Python and is targeted primarily at the single board computer (SBC) platforms like the [Raspberry Pi](https://www.raspberrypi.org/).

## Goals
I'm not sure where we will end up but the goals for this project are pretty simple:

1. Must be able to do every day tasks (tell time, weather, and be context aware)
2. Must provide evidence of "thought" (I'm still working on what exactly this means)
3. Must be fun (because the moment it becomes "work" I'm sure we'll all lose interest)

**NOTICE** - Karen is under development against Python 3.7.  She is not compatible with Python 2 so be sure to use "python3" or "python3.7" (and install the related binaries if needed).

## Installation/System Prep
The following instructions were developed primarily for [RaspberryPi.org](https://www.raspberrypi.org) (Official Raspberry Pi OS), but they should work on most Debian/Ubuntu and derivatives (amd64) although your mileage may vary.  Please shoot us the details on your success or open a thread for failures and we will enhance these instructions.

### General Setup (applies to most systems)
To start with, we need some base packages available in most Debian and Debian-like distros.  These are mostly related to sound and video device access which is needed by deepspeech and opencv.
```
sudo apt-get install python3-pip \
  python3-opencv \
  libatlas-base-dev \
  libqtgui4 \
  libqt4-test \
  python3-pyqt5 \
  pulseaudio \
  pamix \
  pavucontrol \
  libpulse-dev \
  libportaudio2 \
  libasound2-dev \
  festival festvox-us-slt-hts  \
  libjasper-dev
```
Next we need to add some Python specific packages that are dependencies for Karen's code.
```
sudo pip3 install opencv-python \
  opencv-contrib-python \
  pyaudio \
  Pillow \
  webrtcvad \
  halo \
  scipy \
  deepspeech
```

Next, install the visualizer program called "vis".  It's a pretty simple compile.  The project is hosted on Github as [dpayne/cli-visualizer](https://github.com/dpayne/cli-visualizer)
```
sudo apt-get install libfftw3-dev libncursesw5-dev cmake
sudo apt-get install libpulse-dev

cd /tmp
wget https://github.com/dpayne/cli-visualizer/archive/master.zip
unzip master.zip
cd cli-visualizer-master

export ENABLE_PULSE=1
./install.sh
```

Once "vis" is installed you may need to set the audio device.  See the Other Notes on how to get a list of device IDs but you can add the device in the "~/.config/vis/config" file
```
echo "audio.pulse.source=1" >> ~/.config/vis/config
```
### Ubuntu Setup
Ubuntu uses pulseaudio by default so much of the setup for audio in/out should be very straight forward.  If you're installing without a GUI then check out the details with the Raspberry Pi.
```
sudo apt-get install portaudio19-dev python3-pyaudio
```

### Raspberry Pi Configuration
WARNING:  The Raspberry Pi 4 (and prior) does not have a built-in Microphone.  No idea why that wasn't included but it wasn't so you'll need add one either via USB or expansion board.  They're pretty cheap on Amazon (around $4).

Make sure you enable the camera in the Pi if that's what you're using.  It's simple to turn on.  Use the "raspi-config" command, or if you're on the command line then try out:
```
sudo -s raspi-config
```
Next, while you shouldn't need it, but just in case I'm listing it here for your review in the event you need to modprobe the sound driver for the onboard output on the Pi.
```
sudo modprobe snd_bcm2835 
```

We also need to add a reference for a library in our .bashrc file to meet some of the dependencies of the software we installed above.  This should run under the user that will be executing the Karen program.  (You can also set this at runtime by prefixing it in the command call if you're not using a standard logged in user to start it up.)
```
echo "" >> ~/.bashrc
echo "export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1" >> ~/.bashrc
```

Also, if you followed the general steps then you should have pulse audio installed now.  You will want to make sure that it is started before continuing.
```
pulseaudio --start
```

Next we need to configure output to Festival.  Festival will reference a file in the user's home directory just like the .bashrc above.  You can also set this in /etc, but we'll keep it simple with the following:
```
echo "(Parameter.set 'Audio_Required_Format 'aiff)" > ~/.festivalrc
echo "(Parameter.set 'Audio_Command \"paplay $FILE --client-name=Festival --stream-name=Speech -d 1\")" >> ~/.festivalrc
echo "(Parameter.set 'Audio_Method 'Audio_Command)" >> ~/.festivalrc
echo "(set! voice_default 'voice_cmu_us_slt_arctic_hts)" >> ~/.festivalrc
```
BE ADVISED that you must know the device index to use the above.  Change the "-d 1" to the index number of the device you're using for output from pulse audio.  See the "Other Notes" section on how to list devices by their index.  You can set the default devices inside the control panels, but I've found that you may want to go a different route and often it's difficult to use those tools if you don't install a full desktop.  (For those asking, YES the Raspberry Pi can output sound via HDMI and it also has the standard headphone jack, but these show up as separate devices so you may have to pick one.)

Once you've got it installed you can test it out by following the details in the Other Notes section below.


## Other Notes
Here are a few additional notes that you may find helpful in your setup.

### Listing Audio Devices by Device ID
Inevitably you are going to need to know your device IDs for your input and output devices.  This is especially true on the Raspberry Pi.  The good news is that it is relatively simple once Pulse Audio is installed.  Here are the commands.
```
# List Microphones/Inputs
pacmd list-sources | grep -e "index:" -e device.string -e "name:" 

# List Outputs
pacmd list-sinks | grep -e "index:" -e device.string -e "name:"
```

### Testing Audio In/Out
Once you have what you think to be the correct device IDs you can test it out with one or more of the following commands.
```
# Testing audio output
paplay -d 1 /usr/share/sounds/alsa/Front_Center.wav

# Testing audio input/recording
parecord -d 1 test.wav
```

### Testing Speech-To-Text through Festival
You can convert any text you want into voice using festival's --tts switch.  It works as follows:
```
echo "Testing speech" | festival --tts
```

### Models
Karen uses prebuilt models for face and speech recognition.  These are freely available from the links below.


* [Face Recognition](https://github.com/opencv/opencv/tree/master/data/haarcascades)
```
wget https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml
```

* [Speech Recognition](https://github.com/mozilla/DeepSpeech/releases/tag/v0.7.3)  
```
wget https://github.com/mozilla/DeepSpeech/releases/download/v0.7.3/deepspeech-0.7.3-models.tflite
wget https://github.com/mozilla/DeepSpeech/releases/download/v0.7.3/deepspeech-0.7.3-models.pbmm
wget https://github.com/mozilla/DeepSpeech/releases/download/v0.7.3/deepspeech-0.7.3-models.scorer
```
*Note that the Raspberry Pi uses tflite whereas AMD64 will use PBMM due to resource constraints on the Pi.


## Other Links &amp; Details
Follow my journey on Twitter [@lnxusr1](https://twitter.com/lnxusr1)

