'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Handler routines for brain and devices
'''

import time 

def handleKillCommand(jsonRequest):
    """
    Stops the TCP server and all dependent services
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """
    
    jsonRequest.container.logger.debug("KILL received.")
    jsonRequest.sendResponse(False, "Server is shutting down")
    return jsonRequest.container.stop()

def brain_handleAudioInputData(jsonRequest):
    """
    Accepts incoming speech-to-text samples, saves them to the data catalog, and processes to determine appropriate response.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success else raises an exception.
    """

    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        return jsonRequest.sendResponse(True, "Invalid AUDIO_INPUT received.")
    
    jsonRequest.container.logger.info("(" + str(jsonRequest.payload["type"]) + ") " + str(jsonRequest.payload["data"]))
    jsonRequest.container.addData(jsonRequest.payload["type"], jsonRequest.payload["data"])
    jsonRequest.sendResponse(message="Data collected successfully.")
    
    # Handle ask function as a drop-out on the audio_input... if it is an inbound function then we go straight back to the skill callout.
    if "ask" in jsonRequest.container._callbacks and jsonRequest.container._callbacks["ask"]["expires"] != 0:
        if jsonRequest.container._callbacks["ask"]["expires"] >= time.time():
            jsonRequest.container._callbacks["ask"]["expires"] = 0
            jsonRequest.container._callbacks["ask"]["function"](jsonRequest.payload["data"])
            return True
    
    # Do something
    jsonRequest.container.skill_manager.parseInput(str(jsonRequest.payload["data"]))
    
    return True

def brain_handleKillAllCommand(jsonRequest):
    """
    Sends KILL signal to all connected devices and terminates local instance upon completion.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    jsonRequest.container.logger.debug("KILL_ALL received.")
    retVal = jsonRequest.container.sendRequestToDevices("control", { "command": "KILL" })
            
    ret = jsonRequest.sendResponse(False, "All services are shutting down.")
        
    return jsonRequest.container.stop()

def brain_handleRelayCommand(jsonRequest):
    """
    Relays a command received from the brain to all connected clients.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = jsonRequest.container.sendRequestToDevices("control", jsonRequest.payload)
        
    if not retVal:
        return jsonRequest.sendResponse(True, "At least one message failed.")

    return jsonRequest.sendResponse(False, "Command completed.")
    
def brain_handleRelayListenerCommand(jsonRequest):
    """
    Relays an inbound request to all karen.Listener devices.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = jsonRequest.container.sendRequestToDevices("control", jsonRequest.payload, "karen.Listener")
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def brain_handleSayData(jsonRequest):
    """
    Accepts incoming data command for speech and calls the brain's say() method.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        jsonRequest.container.logger.error("Invalid payload for SAY command detected")
        return jsonRequest.sendResponse(True, "Invalid payload for SAY command detected.") 
    
    if not jsonRequest.container.say(jsonRequest.payload["data"]):
        jsonRequest.container.logger.error("SAY command failed")
        jsonRequest.sendResponse(True, "An error occurred")
        
    return jsonRequest.sendResponse(False, "Say command completed.") 

def device_handleStartStopListenerCommand(jsonRequest):
    """
    Handles an inbound START/STOP method for a listener.  Stops the listening device but not the client container.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    if "karen.Listener" in jsonRequest.container.objects:
        for item in jsonRequest.container.objects["karen.Listener"]:
            if my_cmd == "START_LISTENER":
                item["device"].start()
            elif my_cmd == "STOP_LISTENER":
                item["device"].stop()
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def device_handleAudioOutCommand(jsonRequest):
    """
    Disables listening temporarily in order to not capture text going through the speaker.  Expects AUDIO_OUT_START and AUDIO_OUT_END commands.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    if my_cmd == "AUDIO_OUT_START":    
        if "karen.Listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["karen.Listener"]:
                item["device"].logger.debug("AUDIO_OUT_START")
                item["device"]._isAudioOut = True
                
        return jsonRequest.sendResponse(False, "Pausing Listener during speech utterence.")
    elif my_cmd == "AUDIO_OUT_END":    
        if "karen.Listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["karen.Listener"]:
                item["device"].logger.debug("AUDIO_OUT_END")
                item["device"]._isAudioOut = False
                
        return jsonRequest.sendResponse(False, "Engaging Listener after speech utterence.")
    else:
        return jsonRequest.sendResponse(True, "Invalid command data.")
    
def device_handleSayCommand(jsonRequest):
    """
    Accepts the inbound SAY command and calls the say() method on the local device to send data to the speaker.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """
    
    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        jsonRequest.container.logger.error("Invalid payload for SAY command detected")
        return jsonRequest.sendResponse(True, "Invalid payload for SAY command detected.") 
    
    if "karen.Speaker" in jsonRequest.container.objects:
        # First we try to send to active speakers physically connected to the same instance
        for item in jsonRequest.container.objects["karen.Speaker"]:
            item["device"].say(str(jsonRequest.payload["data"]))
            return jsonRequest.sendResponse(False, "Say command completed.") 

    return jsonRequest.sendResponse(True, "Speaker not available.") 