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

Visit our main site: https://projectkaren.ai/

Karen's Architecture
--------------------

Karen's architecture is divided into components that each require
separate installation. This is so that you need only install the
portions required for a specific device to enhance compatibility with
devices like the Raspberry Pi Zero W (which does not support the
listener device). The device components are as follows:

**Python Module Overview**

+--------------+-------+-------------------------------------------------------+
| Python       | Type  | Description                                           |
| Module       |       |                                                       |
+==============+=======+=======================================================+
| karen        | Base  | Global start() method, handlers and shared features.  |
+--------------+-------+-------------------------------------------------------+
| karen\_brain | Engin | Main CPU where device containers will send/receive    |
|              | e     | their I/O.                                            |
+--------------+-------+-------------------------------------------------------+
| karen\_devic | Engin | Standalone service for plugins and I/O to the brain.  |
| e            | e     |                                                       |
+--------------+-------+-------------------------------------------------------+
| karen\_liste | Plugi | Audio capture and Speech-to-Text translation for      |
| ner          | n     | AUDIO\_INPUT.                                         |
+--------------+-------+-------------------------------------------------------+
| karen\_watch | Plugi | Video capture and object detection/recognition for    |
| er           | n     | IMAGE\_INPUT.                                         |
+--------------+-------+-------------------------------------------------------+
| karen\_speak | Plugi | Converts Text-to-Speech and plays output audio        |
| er           | n     | through speakers.                                     |
+--------------+-------+-------------------------------------------------------+
| karen\_panel | Plugi | Visual display for use with touchscreen operations.   |
|              | n     |                                                       |
+--------------+-------+-------------------------------------------------------+

**Python Module to Package Mapping**

+-------------------+----------+-------------------------+----------------------------------------+
| Python Module     | to       | PIP Package             | Notes                                  |
+===================+==========+=========================+========================================+
| karen             | **>>**   | karen                   | \*Shared libraries and methods only.   |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_brain      | **>>**   | karen-brain             | \*Includes shared karen modules.       |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_device     | **>>**   | karen-device            | \*Includes shared karen modules.       |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_listener   | **>>**   | karen-plugin-listener   |                                        |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_watcher    | **>>**   | karen-plugin-watcher    |                                        |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_speaker    | **>>**   | karen-plugin-speaker    |                                        |
+-------------------+----------+-------------------------+----------------------------------------+
| karen\_panel      | **>>**   | karen-plugin-panel      |                                        |
+-------------------+----------+-------------------------+----------------------------------------+

In version 0.7.0 and later you are required to install the brain,
device, and any desired plugins explicitly.

Installation
------------

Karen is available through pip, but to use the built-in devices there
are a few extra libraries you may require. Please visit the `Basic
Install <https://docs.projectkaren.ai/en/latest/installation.basic/>`__
page for more details. If you're impatient and don't want to read the
details then the commands below will perform a **full installation**
with all plugins and dependencies.

::

    sudo apt-get install \
      libfann2 \
      python3-fann2 \
      python3-pyaudio \
      python3-pyqt5 \
      festival \
      festvox-us-slt-hts  \
      libportaudio2 \
      libasound2-dev \
      libatlas-base-dev \
      cmake

::

    pip3 install scikit-build # includes skbuild for compiling opencv
    pip3 install karen-brain karen-device karen-listener karen-watcher karen-speaker

**NOTE:** The installation of OpenCV is automatically triggered when you
install karen-plugin-watcher and this may take a while on the Raspberry
Pi OS as it has to recompile some of the libraries. Patience is required
here as the spinner icon appeared to get stuck several times in our
tests... so just let it run until it completes. If it encounters a
problem then it'll print out the error for additional troubleshooting.

Once installed you can create a new instance of Karen using a
`configuration
file <https://docs.projectkaren.ai/en/latest/config.overview/>`__ with
the following:

::

    import karen_listener
    model_type = "pbmm"                         # use "tflite" for Raspberry Pi
    karen_listener.download_models(model_type)  # Downloads models for deepspeech

    import karen
    karen.start()

**NOTE:** Use ``model_type="tflite"`` if running on the Raspberry Pi. If
you have a webcam or video recording device you can also try
``karen.start("video")`` to optionally start the watcher device.

Read more about startup options including starting the Watcher in
`Starting Up <https://docs.projectkaren.ai/en/latest/karen/>`__.

If everything is working properly you should be able to point your
device to the web control panel running on the **Brain** engine to test
it out. The default URL is:

**http://localhost:8080/**

--------------

Help & Support
--------------

Help and additional details is available at https://projectkaren.ai

.. |GitHub license| image:: https://img.shields.io/github/license/lnxusr1/karen
   :target: https://github.com/lnxusr1/karen/blob/master/LICENSE
.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/yt2mp3.svg
.. |Read the Docs| image:: https://img.shields.io/readthedocs/project-karen
.. |GitHub release (latest by date)| image:: https://img.shields.io/github/v/release/lnxusr1/karen

