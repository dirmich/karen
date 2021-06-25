"""
General handlers for TCP requests between device containers and the Brain.
"""

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

def brain_handleImageInputData(jsonRequest):
    """
    Accepts incoming image capture data, saves them to the data catalog, and processes to determine appropriate response.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success else raises an exception.
    """
    
    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        return jsonRequest.sendResponse(True, "Invalid IMAGE_INPUT received.")
    
    jsonRequest.container.logger.info("(" + str(jsonRequest.payload["type"]) + ") " + str(jsonRequest.payload["data"]))
    jsonRequest.container.addData(jsonRequest.payload["type"], jsonRequest.payload["data"])
    
    return jsonRequest.sendResponse(message="Data collected successfully.")

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
    
    if "data" not in jsonRequest.payload or "command" not in jsonRequest.payload["data"]:
        return jsonRequest.sendResponse(True, "Invalid requested command.")
    
    inContainer = str(jsonRequest.payload["data"]["container"]) if "container" in jsonRequest.payload["data"] else None
    inType = str(jsonRequest.payload["data"]["type"]) if "type" in jsonRequest.payload["data"] else None
    inFilter = str(jsonRequest.payload["data"]["name"]) if "name" in jsonRequest.payload["data"] else None
    if inFilter is None:
        inFilter = jsonRequest.payload["data"]["id"] if "id" in jsonRequest.payload["data"] else None
    
    retVal = jsonRequest.container.sendRequestToDevices("control", jsonRequest.payload["data"], inContainer=inContainer, inType=inType, inFilter=inFilter)
    
    if not retVal:
        return jsonRequest.sendResponse(True, "At least one message failed.")
    
    return jsonRequest.sendResponse(False, "Command completed.")
    
def brain_handleRelayListenerCommand(jsonRequest):
    """
    Relays an inbound request to all karen.listener.Listener devices.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = jsonRequest.container.sendRequestToDevices("control", jsonRequest.payload, "karen.listener.Listener")
        
    return retVal

def brain_handleRelayWatcherCommand(jsonRequest):
    """
    Relays an inbound request to all karen.watcher.Watcher devices.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    if my_cmd == "STOP_WATCHER":
        my_cmd = "STOP_DEVICE"
    elif my_cmd == "STOP_LISTENER":
        my_cmd = "STOP_DEVICE"
        
    sendToDevice = { "command": my_cmd, "type": "karen.watcher.Watcher" }
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = jsonRequest.container.sendRequestToDevices("control", sendToDevice, "karen.watcher.Watcher")
        
    return retVal

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
        return jsonRequest.sendResponse(True, "An error occurred")
        
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

    if "karen.listener.Listener" in jsonRequest.container.objects:
        for item in jsonRequest.container.objects["karen.listener.Listener"]:
            if my_cmd == "START_LISTENER":
                item["device"].start()
            elif my_cmd == "STOP_LISTENER":
                item["device"].stop()
                
        jsonRequest.container.registerWithBrain() # Updates the status of the devices.
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def device_handleStartStopCommand(jsonRequest):
    """
    Handles an inbound START/STOP method for a listener.  Stops the listening device but not the client container.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    inType = str(jsonRequest.payload["type"]) if "type" in jsonRequest.payload else None
    inName = str(jsonRequest.payload["name"]) if "name" in jsonRequest.payload else None
    inUUID = str(jsonRequest.payload["uuid"]) if "uuid" in jsonRequest.payload else None

    bChange = False
    for deviceType in jsonRequest.container.objects:
        for item in jsonRequest.container.objects[deviceType]:
            if inType is None or inType == deviceType:
                
                bFound = False
                if inName is None and inUUID is None:
                    bFound = True
                
                elif inName is not None and item["friendlyName"] == inName:
                    bFound = True
                
                elif inUUID is not None and item["uuid"] == inUUID:
                    bFound = True

                if bFound:
                    if my_cmd == "STOP_DEVICE":
                        item["device"].stop()
                        bChange = True

                    if my_cmd == "START_DEVICE":
                        item["device"].start()
                        bChange = True

    if bChange:
        ret = jsonRequest.container.registerWithBrain()
    
    return jsonRequest.sendResponse(False, "Command completed.") 

def device_handleStartStopWatcherCommand(jsonRequest):
    """
    Handles an inbound START/STOP method for a watcher.  Stops the watcher device but not the client container.
    
    Args:
        jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
        
    Returns:
        (bool):  True on success and False on failure.
    """

    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    if "karen.watcher.Watcher" in jsonRequest.container.objects:
        for item in jsonRequest.container.objects["karen.watcher.Watcher"]:
            if my_cmd == "START_WATCHER":
                item["device"].start()
            elif my_cmd == "STOP_WATCHER":
                item["device"].stop()
                
        jsonRequest.container.registerWithBrain() # Updates the status of the devices.
        
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
        if "karen.listener.Listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["karen.listener.Listener"]:
                item["device"].logger.debug("AUDIO_OUT_START")
                item["device"]._isAudioOut = True
                
        return jsonRequest.sendResponse(False, "Pausing Listener during speech utterence.")
    elif my_cmd == "AUDIO_OUT_END":    
        if "karen.listener.Listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["karen.listener.Listener"]:
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
    
    if "karen.speaker.Speaker" in jsonRequest.container.objects:
        # First we try to send to active speakers physically connected to the same instance
        for item in jsonRequest.container.objects["karen.speaker.Speaker"]:
            item["device"].say(str(jsonRequest.payload["data"]))
            return jsonRequest.sendResponse(False, "Say command completed.") 

    return jsonRequest.sendResponse(True, "Speaker not available.") 