# Project Karen &middot; [![GitHub license](https://img.shields.io/github/license/lnxusr1/karen)](https://github.com/lnxusr1/karen/blob/master/LICENSE) [![Python Versions](https://img.shields.io/pypi/pyversions/yt2mp3.svg)](https://github.com/lnxusr1/karen/)
This project is dedicated to building a "Synthetic Human" which is called Karen (for now) for which we have assigned the female gender pronoun of "She". She has visual face recognition ([opencv/opencv](https://github.com/opencv/opencv)), speech transcription ([mozilla/deepspeech](https://github.com/mozilla/DeepSpeech)), and speech synthesis ([festival](http://www.cstr.ed.ac.uk/projects/festival/)).  Karen is written in Python and is targeted primarily at the single board computer (SBC) platforms like the [Raspberry Pi](https://www.raspberrypi.org/).

Visit our main site: [https://projectkaren.ai/](https://projectkaren.ai/)

## Quick Install

Karen is available through pip, but to use the built-in devices there are a few extra libraries you may require.  Please visit the [Basic Install](installation.basic.md) page for more details.  To get started try:

```
pip3 install karen
```

Once installed you can create a new instance of Karen with the following:

```
import karen
karen.start('/path/to/config.json')
```

If everything is working properly you should be able to point your device to the web control panel to test it out.  The default URL is:

__
[http://localhost:8080/webgui](http://localhost:8080/webgui)
__

![Control Panel](https://projectkaren.ai/wp-content/uploads/2021/06/karen_model_0_5_4_control_panel.png)

## Demo running on Raspberry Pi


[![Project Karen](https://projectkaren.ai/wp-content/uploads/2021/06/karen_model_0_1_0_demo3.jpg)](https://projectkaren.ai/static/karen_model_0_1.mp4)