# Basic Audio + Video Example

```
{
	"settings": {
		"libraryFolder": null,
		"skillsFolder": null
	},
	"container": {
		"start": true,
		"friendlyName": "living room",
		"tcp_port": 8081,
		"hostname": null,
		"ssl": {
			"cert_file": null,
			"key_file": null
		},
		"devices": [
			{
				"uuid": null,
				"friendlyName": "mic1",
				"type": "karen.listener.Listener",
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
				"uuid": null,
				"friendlyName": "speaker1",
				"type": "karen.speaker.Speaker"
			},
			{
				"uuid": null,
				"friendlyName": "cam1",
				"type": "karen.watcher.Watcher",
				"parameters": {
					"classifierFile": null,
					"recognizerFile": null,
					"namesFile": null,
					"trainingSourceFolder": null,
					"videoDeviceIndex": null,
					"framesPerSecond": 1.0,
					"orientation": 0
				}
			}
		],
		"commands": [
			{ "type": "KILL", "function": "karen.handlers.handleKillCommand" },
			{ "type": "START_LISTENER", "function": "karen.handlers.device_handleStartStopListenerCommand" },
			{ "type": "STOP_LISTENER", "function": "karen.handlers.device_handleStartStopListenerCommand" },
			{ "type": "START_WATCHER", "function": "karen.handlers.device_handleStartStopWatcherCommand" },
			{ "type": "STOP_WATCHER", "function": "karen.handlers.device_handleStartStopWatcherCommand" },
			{ "type": "AUDIO_OUT_START", "function": "karen.handlers.device_handleAudioOutCommand" },
			{ "type": "AUDIO_OUT_END", "function": "karen.handlers.device_handleAudioOutCommand" },
			{ "type": "SAY", "function": "karen.handlers.device_handleSayCommand" },
			{ "type": "START_DEVICE", "function": "karen.handlers.device_handleStartStopCommand" },
			{ "type": "STOP_DEVICE", "function": "karen.handlers.device_handleStartStopCommand" }
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
			{ "type": "START_WATCHER", "function": "karen.handlers.brain_handleRelayWatcherCommand" },
			{ "type": "STOP_WATCHER", "function": "karen.handlers.brain_handleRelayWatcherCommand" },
			{ "type": "KILL", "function": "karen.handlers.handleKillCommand" },
			{ "type": "RELAY", "function": "karen.handlers.brain_handleRelayCommand", "enableWebControl": false },
			{ "type": "KILL_ALL", "function": "karen.handlers.brain_handleKillAllCommand" }
		],
		"data": [
			{ "type": "SAY", "function": "karen.handlers.brain_handleSayData", "friendlyName": "SAY SOMETHING..." },
			{ "type": "AUDIO_INPUT", "function": "karen.handlers.brain_handleAudioInputData" },
			{ "type": "IMAGE_INPUT", "function": "karen.handlers.brain_handleImageInputData" }
		]
	}
}
```