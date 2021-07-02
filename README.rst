Project Karen · |GitHub license| |Python Versions| |Read the Docs| |GitHub release (latest by date)|
====================================================================================================

This project is dedicated to building a "Synthetic Human" which is
called Karen (for now) for which we have assigned the female gender
pronoun of "She". She has visual face recognition
(`opencv/opencv <https://github.com/opencv/opencv>`__), speech
transcription
(`mozilla/deepspeech <https://github.com/mozilla/DeepSpeech>`__), and
speech synthesis
(`festival <http://www.cstr.ed.ac.uk/projects/festival/>`__). Karen is
written in Python and is targeted primarily at the single board computer
(SBC) platforms like the `Raspberry
Pi <https://www.raspberrypi.org/>`__.

Installation
------------

You will likely need a few extra packages and libraries to run Karen's
core routines. The details on all of this is available on our
installation page at the link below.

https://docs.projectkaren.ai/

::

    sudo apt-get install \
      festival \
      festvox-us-slt-hts  \
      libfann2 \
      python3-fann2 \
      libportaudio2 \
      libasound2-dev \
      cmake

Install with PIP (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    pip3 install karen

Install via Download (Alternative)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure you see the requirements.txt for other python libraries that
are required. The PIP method is recommended as it will automatically
include these dependencies.

::

    cd /path/to/karen
    python3 setup.py install

Get the Mozilla DeepSpeech Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To download the speech models you can use the script below inside a
Python shell or visit the
`DeepSpeech <https://github.com/mozilla/DeepSpeech/releases/latest>`__
page:

::

    import karen
    karen.download_models(version="0.9.3", model_type="pbmm", include_scorer=True)

**NOTE:** The version number is optional and if ommitted it will attempt
to determine your currently installed version and use that to download
the appropriate inference model. Also, you will need to use
``model_type="tflite"`` if you are running on Raspberry Pi.

Starting Up
-----------

There are lots of ways to leverage karen. You can import the device
modules like listener and use on its own or you can start the entire
process. There is a basic configuration file located in the data
directory inside the karen module directory
(``/path/to/karen/data/basic_config.json``).

To run Karen using the default Listener + Speaker configuration try:

::

    import karen
    karen.start()

**NOTE:** If you have a webcam or video recording device you can try
``karen.start("video")`` to optionally start the watcher device or
``karen.start("/path/to/config.json")`` to use a custom configuration.

Read more about startup options including starting the Watcher in
`Starting Up <https://docs.projectkaren.ai/en/latest/karen/>`__.

If everything is working properly you should be able to point your
device to the web control panel to test it out. The default URL is:

**http://localhost:8080/webgui**

*Karen is under development against Python 3. She is not compatible with
Python 2 so be sure to use* ``pip3`` *or* ``python3`` *if appropriate
(and install the related binaries if needed).*

--------------

Help & Support
--------------

Installation instructions and documentation is available at
https://projectkaren.ai

.. |GitHub license| image:: https://img.shields.io/github/license/lnxusr1/karen
   :target: https://github.com/lnxusr1/karen/blob/master/LICENSE
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/yt2mp3.svg
.. |Read the Docs| image:: https://img.shields.io/readthedocs/project-karen
.. |GitHub release (latest by date)| image:: https://img.shields.io/github/v/release/lnxusr1/karen

