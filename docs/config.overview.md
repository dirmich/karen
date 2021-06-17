# Configuration Overview

Karen supports the use of a JSON configuration file to set up all the devices, their callbacks, and their connection to the Brain.  This is made available for those who may want to use Karen but opt to not have to write any Python code.

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

## Configuring the Brain

The Brain is what you might thing.  It is the central processing unit and target for all data collections and inputs.  It's sole purpose is to process those inputs and determine if an output or action should be taken.  If so, then it sends that message out to Device Containers to produce the needed output.

For example, a listening device will collect speech data and send it to the brain.  The brain will use that data to determine intent like say responding to the phrase "Hello".  The brain will then generate an appropriate response or in our case a "Hi there" and send it out to a device container with a speaker to audibly respond to the input.

The brain also is the unit on which the control panel is located.  All control panel commands are sent directly to the brain as it most closely resembles a device container in its request/response activities.

The control panel is available at the Brain's IP address and TCP port as configured.  The defaults for these are localhost and port 8080.  You can view the control panel via __http://localhost:8080/webgui__ or at whatever settings you specify.  If you add an SSL certificate then be sure to also change http:// to https:// in your references where appropriate.

While __the brain config must be present to indicate TCP_PORT and HOSTNAME__, you can also specify ```"start": false``` which will not start a brain engine as part of the current instance.  This would enable you to separate the brain from the input/output devices.

A sample brain configuration is as follows:
```
{
	"brain": {
		"start": true,
		"tcp_port": 8080,
		"hostname": null,
		"ssl": {
		    "use_ssl": false,
			"cert_file": null,
			"key_file": null
		},
		"commands": [
			{ "type": "START_LISTENER", "function": "karen.handlers.brain_handleRelayListenerCommand" },
			{ "type": "STOP_LISTENER", "function": "karen.handlers.brain_handleRelayListenerCommand" },
			{ "type": "KILL", "function": "karen.handlers.handleKillCommand" },
			{ "type": "KILL_ALL", "function": "karen.handlers.brain_handleKillAllCommand" }
		],
		"data": [
			{ "type": "SAY", "function": "karen.handlers.brain_handleSayData", "friendlyName": "SAY SOMETHING..." },
			{ "type": "AUDIO_INPUT", "function": "karen.handlers.brain_handleAudioInputData" }
		]
	}
}
```

### Command Handlers

In this simple example the brain is configured to respond to control commands and data inputs.  The control commands it will handle are START_LISTENER, STOP_LISTENER, KILL, and KILL_ALL.  When the brain receives those commands it in turn calls the related function to handle performing the action and providing the caller a response.  Each of these handlers accepts a karen.shared.KJSONRequest object which includes a container (the brain or device container object), a path (the url to which the command was posted), and a payload.  

Control commands must be POSTED to the "/control" URL (e.g. http://localhost:8080/control) on the brain and must be sent as "application/json" content type.

A sample payload will look like this:

```
{
    "command": "START_LISTENER"
}
```
The payload can contain additional information that would be available in the payload object, but the minimum requirement is that it contain a command value that matches the "type" specified in the callback which is how the brain knows that command is related to that callback handler.

### Data Handlers

The data input works the same way except that its payload is a little different.  Data requests are POSTED to the "/data" URL on the brain and must be sent as "application/json" content type.

```
{
    "type": "AUDIO_INPUT",
    "data": "Hello"
}
```

Here we see the use of the "type" which is a required value that the brain uses to tie the incoming input type back to its related handler.  Additionally it includes a "data" value which can include any data that your handler requires.  In our case its a simple text value of "Hello" which in this example is a basic Listener letting the brain know it heard the word "Hello" from its microphone.

## Setting up a Device Container

A device container is uses as a vehicle to allow one or more input/output devices to connect with the Brain without having to deal with all the communication activities themselves.  A device container has no limit on the type or number of devices for which it can support and will automatically register with the brain and notify the brain of any devices it represents.

Since a device container has no hard and fast requirements on the number or type of devices the configuration file allows you to specify those devices along with their handlers for command processing.

Here's a simple device container configuration with one listener class and one speaker class.  Do make note that the types are the actual full python path and class which will be used to instantiate the object as well as keep it separate from other device types.  Additionally, the parameters are the values that will be passed into the object's \__init__ call.  These should be specified based on whatever device is being created.

```
{
	"container": {
		"start": true,
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"friendlyName": "living room",
				"type": "karen.Listener",
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
				"friendlyName": "living room",
				"type": "karen.Speaker"
			}
		],
		"commands": [
			{ "type": "KILL", "function": "karen.handlers.handleKillCommand" },
			{ "type": "START_LISTENER", "function": "karen.handlers.device_handleStartStopListenerCommand" },
			{ "type": "STOP_LISTENER", "function": "karen.handlers.device_handleStartStopListenerCommand" },
			{ "type": "AUDIO_OUT_START", "function": "karen.handlers.device_handleAudioOutCommand" },
			{ "type": "AUDIO_OUT_END", "function": "karen.handlers.device_handleAudioOutCommand" },
			{ "type": "SAY", "function": "karen.handlers.device_handleSayCommand" }
		]
	}
}
```

### Putting it all Together

Now that we've covered the pieces, it is important to note that some sections are not optional.

You must include a brain section in all configurations.  The brain must at least specify a TCP Port and Hostname.  To specify a device you can leave the brain's "start" value to false if you intend to use another instance to serve the brain routines.

#### A Speaker Device with an External Brain
```
{
	"brain": {
		"start": false,
		"tcp_port": 8080,
		"hostname": "my-brain-server.mydomain.com"
	},
	"container": {
		"start": true,
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"friendlyName": "living room",
				"type": "karen.Speaker"
			}
		],
		"commands": [
			{ "type": "KILL", "function": "karen.handlers.handleKillCommand" },
			{ "type": "SAY", "function": "karen.handlers.device_handleSayCommand" }
		]
	}
}
```