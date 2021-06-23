# Raspberry Pi

## Video

Make sure you enable the camera in the Pi if that's what you're using.  It's simple to turn on.  Use the "raspi-config" command, or if you're on the command line then try out:
```
sudo -s raspi-config
```

## Audio

I tend to like the pulseaudio setup since it gives a bit more control (in my opinion) over the default setup.  The installation is pretty simple.  here are the packages and they are totally optional.

```
sudo apt-get install libatlas-base-dev \
  pulseaudio \
  pamix \
  pavucontrol \
  libpulse-dev
```

Next, you shouldn't need it, but just in case I'm listing it here for your review in the event you need to modprobe the sound driver for the onboard output on the Pi.
```
sudo modprobe snd_bcm2835 
```

We may need also to add a reference for a library in our .bashrc file to meet some of the dependencies of the software that is required.  This should run under the user that will be executing the Karen program.  (You can also set this at runtime by prefixing it in the command call if you're not using a standard logged in user to start it up.)
```
echo "" >> ~/.bashrc
echo "export LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1" >> ~/.bashrc
```

Also, if you followed the general steps then you should have pulse audio installed now.  You will want to make sure that it is started before continuing.
```
pulseaudio --start
```

