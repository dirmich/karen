# Project Karen &middot; [![GitHub license](https://img.shields.io/github/license/lnxusr1/karen)](https://github.com/lnxusr1/karen/blob/master/LICENSE) ![Python Versions](https://img.shields.io/pypi/pyversions/yt2mp3.svg) ![Read the Docs](https://img.shields.io/readthedocs/project-karen) ![GitHub release (latest by date)](https://img.shields.io/github/v/release/lnxusr1/karen)

This project is dedicated to building a "Synthetic Human" which is called Karen (for now) for which we have assigned the female gender pronoun of "She". She has visual face recognition ([opencv/opencv](https://github.com/opencv/opencv)), speech transcription ([mozilla/deepspeech](https://github.com/mozilla/DeepSpeech)), and speech synthesis ([festival](http://www.cstr.ed.ac.uk/projects/festival/)).  Karen is written in Python and is targeted primarily at the single board computer (SBC) platforms like the [Raspberry Pi](https://www.raspberrypi.org/).

Visit our main site: [https://projectkaren.ai/](https://projectkaren.ai/)

## Quick Install

Karen is available through pip, but to use the built-in devices there are a few extra libraries you may require.  Please visit the [Basic Install](installation.basic.md) page for more details.  To get started try:

```
sudo apt-get install \
  festival \
  festvox-us-slt-hts  \
  libfann2 \
  python3-fann2 \
  libportaudio2 \
  libasound2-dev \
  libatlas-base-dev \
  cmake
```

```
pip3 install karen
```
__NOTE:__ The installation of OpenCV is automatically triggered when you install Karen and this may take a while on the Raspberry Pi OS (buster) as it has to recompile some of the libraries.  Patience is required here as the spinner icon appeared to get stuck several times in our tests... but just let it run until it completes.  If it encounters a problem then it'll print out the error for more troubleshooting.

Once installed you can create a new instance of Karen using a [configuration file](config.overview.md) with the following:

```
import karen
karen.download_models(model_type="pbmm")
karen.start()
```

__NOTE:__ Use ```model_type="tflite"``` if running on the Raspberry Pi.  If you have a webcam or video recording device you can also try ```karen.start("video")``` to optionally start the watcher device.

Read more about startup options including starting the Watcher in [Starting Up](karen.md).

If everything is working properly you should be able to point your device to the web control panel to test it out.  The default URL is:

__
[http://localhost:8080/webgui](http://localhost:8080/webgui)
__

![Control Panel](https://projectkaren.ai/wp-content/uploads/2021/06/karen_model_0_5_4_control_panel.png)

## Demo running on Raspberry Pi


[![Project Karen](https://projectkaren.ai/wp-content/uploads/2021/06/karen_model_0_1_0_demo3.jpg)](https://projectkaren.ai/static/karen_model_0_1.mp4)