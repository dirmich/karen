# Configuration Overview

Karen supports the use of a JSON configuration file to set up all the devices, their callbacks, and their connection to the Brain.  This is made available for those who may want to use Karen but opt to not have to write any Python code.

* Skip ahead to the [full Configuration Example](config.example.md)

## Global Settings

Karen can be made to import 3rd party libraries that are located outside of her primary folders.  This is done by adding a libraryFolder setting.  This will add a location to the PYTHONPATH variable leveraged during runtime.  Your libraries can then be referenced relative to that location.

To add the value add the following under "settings" in the configuration file:
```
{
	"settings": {
	    "libraryFolder": "/path/to/3rdParty/lib"
	}
}
```

If you want to keep a library of skills you create separate you can do so by adding a Skill folder to your configuration and placing your skills there.  Be careful though that if you specify this setting it will override the default skills so if you want to maintain access to the built-in skills you'd need to copy them to your new folder as well.

The Skill Folder setting is as follows:
```
{
	"settings": {
	    "skillsFolder": "/path/to/root/skill/folder"
	}
}
```

Beneath your skill folder you should have your skills each located in a separate folder in the structure:
```
-> /path/to/root/skill/folder
   -> /HelloSkill
      -> /__init__.py
      -> /vocab
         -> /en_us
            -> hello.dialog
            -> hello.intent
```

## Authentication

Karen allows for key-based authentication between the devices and the brain.  If this authentication is enabled then it will also allow for a login user/password to be set for the web control panel.  These can be set in the global settings portion of the config as follows:

```
{
	"settings": {
		"authentication": {
			"key": "ac2f81b0-6eaf-4726-8ede-e45bbc85ecb2",
			"username": "admin",
			"password": "admin"
		}
	}
}
```
To disable authentication then either remove the section or set the key to null as ```"key": null```.  The default configuration does not use authentication.

## Configuring the Brain

The Brain is what you might think.  It is the central processing unit and target for all data collections and inputs.  Its sole purpose is to process those inputs and determine if an output or action should be taken.  If so then it sends that message out to Device Containers to produce the needed output.

For example, a listening device will collect speech data and send it to the brain.  The brain will use that data to determine intent--for example to respond to the phrase "Hello".  The brain will then generate an appropriate response or in our case a "Hi there" and send it out to a device container with a speaker to audibly respond to the input.

The brain is the unit on which the control panel is located.  All control panel commands are sent directly to the brain as it most closely resembles a device container in its request/response activities.

The control panel is available at the Brain's IP address and TCP port as configured.  The defaults for these are localhost and port 8080.  You can view the control panel via __http://localhost:8080__ or at whatever settings you specify.  If you add an SSL certificate then be sure to also change http:// to https:// in your references where appropriate.

While __the brain config must be present to indicate TCP_PORT and HOSTNAME__, you can also specify ```"start": false``` which will not start a brain engine as part of the current instance.  This would enable you to separate the brain from the input/output devices.

A sample brain configuration is as follows:
```
{
	"brain": {
		"start": true,
		"groupName": "core",
		"tcp_port": 8080,
		"hostname": null,
		"startUPNP": true,
		"ssl": {
		    "use_ssl": false,
			"cert_file": null,
			"key_file": null
		}
	}
}
```

### Command Handlers

You can send custom and built-in commands to Karen via the brain or directly to a container device.  The basic format for brain commands is "/brain/COMMAND" where "COMMAND" is a command for which the brain device itself will listen.  You can send commands to containers as "/container/DEVICE_ID/COMMAND" and devices with "/device/DEVICE_ID/COMMAND" where DEVICE_ID is the uuid of the device and the COMMAND is a command the device is set to accept via its internal configuration.

A device can expose a method as a command by adding it to its internal "accepts" value.  All devices must expose an accepts property that should return a list of string values when accessed (e.g. ```speaker.accepts = ["start","stop","speak"]```).

An alternative method to calling a command is to send a JSON payload to /device/DEVICE_ID/instance and include in the payload at the root level a value called ```command``` as follows:

```
{
    "command": "speak",
    "text": "Hello world"
}
```

In this case the command ```speak``` is substituted for being included in the URL.  You can call commands by either method as both perform the same processes.

POST'ed commands should be sent to the desired URL (e.g. http://localhost:8080/device/DEVICE_ID/instance) on the brain and must be sent as "application/json" content type.

The payload can contain additional information and all of the data is sent to the target method via a KHTTPHandler object.

### Data Handlers

Any data collected can be sent and stored in the brain by making a POST request to the brain URL and path ```/brain/collect``` and the data provided must be in JSON format with keys "type" and "data" at the root level.  The brain will automatically store the last 50 values per type in memory for accessing via skills or other methods.

A sample JSON payload to the collect routine would look as follows:

```
{
    "type": "AUDIO_INPUT",
    "data": "Hello"
}
```

Alternatively you can send the collect call to "/brain/instance" and include the "command" value of "collect" as a 3rd root key in the payload.

## Setting up a Device Container

A device container is uses as a vehicle to allow one or more input/output devices to connect with the Brain without having to deal with all the communication activities themselves.  A device container has no limit on the type or number of devices for which it can support and will automatically register with the brain and notify the brain of any devices it represents.

Since a device container has no hard and fast requirements on the number or type of devices the configuration file allows you to specify those devices along with their handlers for command processing.

Here's a simple device container configuration with one listener class and one speaker class.  Do make note that the types are the actual full python path and class which will be used to instantiate the object as well as keep it separate from other device types.  Additionally, the parameters are the values that will be passed into the object's \__init__ call.  These should be specified based on whatever device is being created.

```
{
	"container": {
		"start": true,
		"groupName": "Living Room",
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"uuid": null,
				"type": "karen_listener.Listener",
				"parameters": {
					"speechModel": null,
					"speechScorer": null,
					"audioChannels": 1,
					"audioSampleRate": 16000,
					"vadAggressiveness": 1,
					"speechRatio": 0.75,
					"speechBufferSize": 50,
					"speechBufferPadding": 350,
					"audioDeviceIndex": null
				}
			},
			{
				"type": "karen_speaker.Speaker"
			}
		]
	}
}
```

### Speaker Device with an External Brain

Now that we've covered the pieces, it is important to note that depending on your configuration you may need some extra sections.

For example, if you do not enable UPNP on the brain then you must include a brain section in all the device configurations.  The brain section in this case must at least specify a TCP Port and Hostname.  To specify a device-only without starting a brain you can leave the brain's "start" value to false if you intend to use another instance to serve the brain routines.

#### Device using UPNP to find the Brain on the network
```
{
	"container": {
		"start": true,
		"groupName": "Living Room",
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"type": "karen_speaker.Speaker"
			}
		]
	}
}
```

#### Device with specified Brain connection
```
{
	"brain": {
		"start": false,
		"tcp_port": 8080,
		"hostname": "192.168.0.122"
	},
	"container": {
		"start": true,
		"groupName": "Living Room",
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"type": "karen_speaker.Speaker"
			}
		]
	}
}
```