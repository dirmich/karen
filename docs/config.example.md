# Configuration Example

```
{
	"settings": {
		"libraryFolder": null,
		"skillsFolder": null
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
	},
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