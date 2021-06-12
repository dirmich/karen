import logging
import time
from datetime import datetime
import socket
import threading
import ssl
import random
import json 
import os
import urllib3
import requests
from urllib.parse import urljoin

from .shared import threaded, sendHTTPResponse, KHTTPRequestHandler, KJSONRequest, sendJSONRequest
#from .listener import Listener
from .skillmanager import SkillManager

from . import __version__, __app_name__

def handleAudioInputData(jsonRequest):

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

def handleBrainKillAllCommand(jsonRequest):
    
    jsonRequest.container.logger.debug("KILL_ALL received.")
    retVal = True
    for device in jsonRequest.container.clients:
        if device["active"]:
            ret, msg = sendJSONRequest(urljoin(device["url"],"control"), { "command": "KILL" })
            if not ret:
                retVal = False
            
    ret = jsonRequest.sendResponse(False, "All services are shutting down.")
    if not ret:
        retVal = False
        
    return jsonRequest.container.stop()

def handleBrainKillCommand(jsonRequest):
    #KILL commands are for a single instance termination.  May be received at any node and will not be relayed to the brain.
    
    jsonRequest.container.logger.debug("KILL received.")
    jsonRequest.sendResponse(False, "Server is shutting down")
    return jsonRequest.container.stop()

def handleBrainRelayCommand(jsonRequest):
    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = True
    for device in jsonRequest.container.clients:
        ret, msg = sendJSONRequest(urljoin(device["url"],"control"), jsonRequest.payload)
        if not ret:
            retVal = False
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def handleBrainRelayListenerCommand(jsonRequest):
    my_cmd = jsonRequest.payload["command"]
    jsonRequest.container.logger.debug(my_cmd + " received.")
    
    jsonRequest.sendResponse(False, "Command completed.") 
    retVal = True
    for device in jsonRequest.container.clients:
        if device["active"] and device["devices"]["listener"] > 0:
            ret, msg = sendJSONRequest(urljoin(device["url"],"control"), jsonRequest.payload)
            if not ret:
                retVal = False
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def handleBrainSayData(jsonRequest):
    #SAY command is not relayed to the brain.  It must be received by the brain or a speaker instance directly.
    
    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        jsonRequest.container.logger.error("Invalid payload for SAY command detected")
        return jsonRequest.sendResponse(True, "Invalid payload for SAY command detected.") 
    

    if not jsonRequest.container.say(jsonRequest.payload["data"]):
        jsonRequest.container.logger.error("SAY command failed")
        jsonRequest.sendResponse(True, "An error occurred")
    return jsonRequest.sendResponse(False, "Say command completed.") 

class Brain(object):
    def __init__(self, **kwargs):

        self._lock = threading.Lock()   # Lock for daemon processes
        self._socket = None             # Socket object (where the listener lives)
        self._thread = None             # Thread object for TCP Server (Should be non-blocking)
        self._deviceThread = None       # Thread object for device checks (runs every 5 seconds to confirm devices are active)
        self._isRunning = False         # Flag used to indicate if TCP server should be running
        self._threadPool = []           # List of running threads (for incoming TCP requests)
        
        self.skill_manager = SkillManager(self)
        self.skill_manager.initialize()
        
        self._callbacks = {}
        self._actionCommands = []
        self._dataCommands = []
        
        self._data = {}
        self.clients = []               # { "url": "http://", "active": true }
        self._handlers = {}
        self._dataHandlers = {}
        
        self.logger = logging.getLogger("BRAIN")
        self.httplogger = logging.getLogger("HTTP")
        
        # TCP Command Interface
        self.tcp_port = 8080            # TCP Port for listener.
        self.hostname = "localhost"     # TCP Hostname
        self.use_http = True
        self.keyfile=None
        self.certfile=None
        
        self.isOffline = None 
        self.webgui_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "web")
                        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.
        
        self.my_url = "http://"
        if not self.use_http:
            self.my_url = "https://"
        self.my_url = self.my_url + str(self.hostname) + ":" + str(self.tcp_port)
        
        self.setHandler("START_LISTENER", handleBrainRelayListenerCommand)
        self.setHandler("STOP_LISTENER", handleBrainRelayListenerCommand)
        self.setHandler("KILL", handleBrainKillCommand)
        self.setHandler("KILL_ALL", handleBrainKillAllCommand)
        #self.setHandler("AUDIO_OUT_START", handleAudioOutCommand)
        #self.setHandler("AUDIO_OUT_END", handleAudioOutCommand)
        
        self.setDataHandler("SAY", handleBrainSayData, friendlyName="SAY SOMETHING...")
        self.setDataHandler("AUDIO_INPUT",handleAudioInputData)
        
    @threaded
    def _acceptConnection(self, conn, address):
        
        try:
            r = KHTTPRequestHandler(conn.makefile(mode='b'))
            path = str(r.path).lower()
            if ("?" in path):
                path = path[:path.index("?")]
            
            payload = {}
            if r.command.lower() == "post":
                payload = r.parse_POST()
            else:
                payload = r.parse_GET()
            
            self.httplogger.debug("BRAIN (" + str(address[0]) + ") " + str(r.command) + " " + str(path))
            
            req = KJSONRequest(self, conn, path, payload)
            if (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
                return self.processCommandRequest(req)
            
            elif (len(path) == 5 and path == "/data") or (len(path) > 5 and path[:6] == "/data/"):
                return self.processDataRequest(req)
            
            elif (len(path) == 7 and path == "/status") or (len(path) > 7 and path[:8] == "/status/"):
                return self.processStatusRequest(req)

            elif (len(path) == 9 and path == "/register") or (len(path) > 9 and path[:10] == "/register/"):
                self.registerClient(address, req)
            
            elif (len(path) == 7 and path == "/webgui") or (len(path) > 7 and path[:8] == "/webgui/"):
                return self.processFileRequest(conn, path, payload)
            
            elif path == "/favicon.ico" or path == "/webgui/favicon.ico":
                response_type = "image/svg+xml"
                myfile = os.path.join(self.webgui_path, "favicon.svg")
                with open(myfile, mode='r') as f:
                    response_body = f.read()
                    
                return sendHTTPResponse(conn, responseType=response_type, responseBody=response_body)
            
            else:
                return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
        except:
            req = KJSONRequest(self, conn, None, None)
            return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
    
    @threaded
    def _tcpServer(self):
        
        self._isRunning = True 
                
        self._lock.acquire()

        self._socket = socket.socket()
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.hostname, self.tcp_port))
        self._socket.listen(self.tcp_clients)
        
        if self.use_http == False:
            self.httplogger.debug("SSL Enabled.")
            self._socket = ssl.wrap_socket(self._socket, 
                                       keyfile=self.keyfile, 
                                       certfile=self.certfile,
                                       server_side=True)
            
        self._lock.release()

        while self._isRunning:

            try:
                # Accept the new connection
                conn, address = self._socket.accept()
                
                t = self._acceptConnection(conn, address)
                
                i = len(self._threadPool) - 1
                while i >= 0:
                    try:
                        if self._threadPool[i] is None or self._threadPool[i].isAlive() == False:
                            self._threadPool.pop(i)
                    except:
                        self._threadPool.pop(i)
                        
                    i = i - 1
                
                self._threadPool.append(t)
                    
            except (KeyboardInterrupt): # Occurs when we press Ctrl+C on Linux
                
                # If we get a KeyboardInterrupt then let's try to shut down cleanly.
                # This isn't expected to be hit as the primary thread will catch the Ctrl+C command first
                
                self.httplogger.info("Ctrl+C detected.  Shutting down.")
                self.stop()  # Stop() is all we need to cleanly shutdown.  Will call child class's method first.
                
                return True # Nice and neat closing
                
            except (OSError): # Occurs when we force close the listener on stop()
                
                pass    # this error will be raised on occasion depending on how the TCP socket is stopped
                        # so we put a simple "ignore" here so it doesn't fuss too much.
        
        return True
    
    @threaded
    def _startDeviceChecks(self):
        
        if self.brain_url is None:
            return True
        
        checkCounter = 1
        checkEvery = 5
        
        while self._isRunning:
            time.sleep(1)
            if checkCounter == checkEvery:
                checkCounter = 0
                for device in self.clients:
                    active = device["active"] if "active" in device else False
                    url = device["url"] if "url" in device else None
                    tryStep = int(device["try"]) if "try" in device else 1
                    
                    if active and url is not None:
                        ret, msg = self._sendRequest("status", {})
                        if not ret:
                            self.logger.error("Unable to connect to device @ " + str(url))
                            device["active"] = False
                            active = False
                        
                        if active:
                            try:
                                msg = json.loads(msg)
                                if msg["error"]:
                                    tryStep = tryStep + 1
                                    device["try"] = tryStep
                                    if tryStep <= 1:
                                        self.logger.warning("(" + str(url) + ") " + str(msg["message"]))
                                    else:
                                        self.logger.error("(" + str(url) + ") " + str(msg["message"]))
                                        device["active"] = False
                                        active = False
                            except:
                                self.logger.error("Unable to parse response from device @ " + str(url))
                                self.logger.debug(str(msg))
                                tryStep = tryStep + 1
                                device["try"] = tryStep
                                if tryStep > 1:
                                    device["active"] = False
                                    active = False
            
            checkCounter = checkCounter + 1
            
    def registerClient(self, address, jsonRequest):
        client_ip = str(address[0])
        client_port = jsonRequest.payload["port"] if "port" in jsonRequest.payload else None
        client_proto = "https://" if "useHttp" in jsonRequest.payload and not jsonRequest.payload["useHttp"] else "http://"
        if client_ip is None or client_port is None:
            jsonRequest.sendResponse(True, "Invalid client address or port detected")
            return False
        
        client_url = client_proto + client_ip + ":" + str(client_port)
        
        bFound = False
        for device in self.clients:
            if device["url"] == client_url:
                bFound = True
                device["active"] = True
                device["devices"] = jsonRequest.payload["devices"] if "devices" in jsonRequest.payload else None
        
        if not bFound:
            self.clients.append({ "url": client_url, "active": True, "devices": jsonRequest.payload["devices"] if "devices" in jsonRequest.payload else None })
        
        return jsonRequest.sendResponse(False, "Registered successfully")
            
    def addData(self, inType, inData):
        if inType is not None and inType not in self._data:
            self._data[inType] = []
            
        self._data[inType].insert(0, { "data": inData, "time": time.time() } )
        if len(self._data[inType]) > 50:
            self._data[inType].pop()
            
        return True
    
    def setHandler(self, handlerType, handlerCallback, enableWebControl=True, friendlyName=None):
        self._handlers[handlerType] = handlerCallback
        if enableWebControl:
            bFound = False
            for item in self._actionCommands:
                if item["type"] == handlerType:
                    bFound = True
                    item["friendlyName"] = friendlyName
                    break
            
            if not bFound:
                self._actionCommands.append({ "type": handlerType, "friendlyName": friendlyName })

        return True
    
    def setDataHandler(self, handlerType, handlerCallback, enableWebControl=True, friendlyName=None):
        self._dataHandlers[handlerType] = handlerCallback

        if enableWebControl:
            bFound = False
            for item in self._dataCommands:
                if item["type"] == handlerType:
                    bFound = True
                    item["friendlyName"] = friendlyName
                    break
            
            if not bFound:
                self._dataCommands.append({ "type": handlerType, "friendlyName": friendlyName })

        return True
    
    def sendRequestToDevices(self, path, payload):
        ret = True 
        
        for device in self.clients:
            
            url = device["url"] if "url" in device else None
            if url is None:
                continue
            
            active = device["active"] if "active" in device else False
            if not active:
                continue
            
            tgtPath = urljoin(url, path)

            if not self._sendRequest(path, payload):
                self.logger.error("Request failed to " + tgtPath)
                self.logger.debug(json.dumps(payload))
                ret = False 
        
        return ret
    
    def processStatusRequest(self, jsonRequest):
        if jsonRequest.path == "/status/devices":
            if "command" in jsonRequest.payload and str(jsonRequest.payload["command"]).lower() == "get-all-current":
                return jsonRequest.sendResponse(False, "Device list completed.", data=self.clients )
            else:
                return jsonRequest.sendResponse(True, "Invalid command.", http_status_code=500, http_status_message="Internal Server Error")
        
        return jsonRequest.sendResponse(False, "Brain is online.")
        
    def processFileRequest(self, conn, path, payload):
        path = path.replace("/../","/").replace("/./","/") # Ugly parsing.  Probably should regex this for validation.
            
        if path == "/webgui" or path == "/webgui/":
            path = "/webgui/index.html"
        
        myfile = os.path.join(self.webgui_path, path[8:])
        if os.path.exists(myfile):
            responseCode = "200",
            responseStatus = "OK"
            response_type = "text/html"
            with open(myfile, mode='r') as f:
                response_body = f.read()
                
            actionCommands = []
            for item in self._actionCommands:
                itemName = item["friendlyName"] if item["friendlyName"] is not None else item["type"]
                actionCommands.append("<button rel=\"" + str(item["type"]) + "\" class=\"command\">" + str(itemName) + "</button>")

            dataCommands = []
            for item in self._dataCommands:
                itemName = item["friendlyName"] if item["friendlyName"] is not None else item["type"]
                dataCommands.append("<option value=\"" + str(item["type"]) + "\">" + str(itemName) + "</option>")

            response_body = response_body.replace("__COMMAND_LIST__", "\n".join(actionCommands))                
            response_body = response_body.replace("__DATA_LIST__", "\n".join(dataCommands))                
            response_body = response_body.replace("__APP_NAME__", __app_name__).replace("__APP_VERSION__", "v"+__version__)
        else:
            responseCode = "404",
            responseStatus = "Not Found"
            response_type = "text/html"
            response_body = "<html><body>File not found</body></html>"  
    
        return sendHTTPResponse(conn, responseType=response_type, responseBody=response_body, httpStatusCode=responseCode, httpStatusMessage=responseStatus)
    
    def processDataRequest(self, jsonRequest):

        if "type" not in jsonRequest.payload or jsonRequest.payload["type"] is None:
            return jsonRequest.sendResponse(True, "Invalid data object.")
        
        my_cmd = str(jsonRequest.payload["type"])
        if my_cmd in self._dataHandlers:
            return self._dataHandlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid data received.")

        return True
    
    def processCommandRequest(self, jsonRequest):
        my_cmd = str(jsonRequest.payload["command"]).upper().strip()
        if my_cmd in self._handlers:
            return self._handlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid command.")
    
    def ask(self, in_text, in_callback=None, timeout=0):
        ret = self.say(in_text)
        if in_callback is not None:
            self._callbacks["ask"] = { "function": in_callback, "timeout": timeout, "expires": time.time()+timeout }
        return True 
    
    def say(self, text):
        speaker = None
        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "speaker" in item["devices"] and item["devices"]["speaker"] >= 0:
                    speaker = item["url"]
                    break
        
        if speaker is None:
            self.logger.warning("SAY: No speaker identified")
            return False
        
        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "listener" in item["devices"] and item["devices"]["listener"] > 0:
                    sendJSONRequest(urljoin(item["url"],"control"), { "command": "AUDIO_OUT_START" })

        sendJSONRequest(urljoin(speaker,"control"), { "command": "SAY", "data": str(text) })


        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "listener" in item["devices"] and item["devices"]["listener"] > 0:
                    sendJSONRequest(urljoin(item["url"],"control"), { "command": "AUDIO_OUT_END" })
            
        return True
    
    def start(self, useThreads=True):

        if self._isRunning:
            return True 

        self._thread = self._tcpServer()
        self.logger.info("Started @ "+ str(self.my_url))

        #self._deviceThread = self._startDeviceChecks()
        
        if not useThreads:
            self._thread.join()
            self._deviceThread.join()

        return True

    def wait(self, seconds=0):
        """Waits for any active servers to complete before closing"""

        if not self._isRunning:
            return True 
                
        if seconds > 0:
            self.logger.info("Shutting down in "+str(seconds)+" second(s).")
            for i in range(0,seconds):
                if self._isRunning:
                    time.sleep(1)
            
            if self._isRunning and self._thread is not None:
                self.stop()
        
        
        if self._thread is not None:
            self._thread.join()
            
        if self._deviceThread is not None:
            self._deviceThread.join()
        
        self.stopDevices()
        
        return True

    def stop(self, stopAllDevices=False):
        
        if not self._isRunning:
            return True 
        
        self._isRunning = False 
        
        if self._socket is not None:
            
            self._lock.acquire()
            
            # Force the socket server to shutdown
            self._socket.shutdown(0)
            
            # Close the socket
            self._socket.close()
            
            self._lock.release()

            # Clear the socket object for re-use
            self._socket = None
        
        if self._deviceThread is not None:
            self._deviceThread.join()
            
        if stopAllDevices:
            self.stopDevices()
        
        self.logger.info("Stopped")
            
        return True
    
    def stopDevices(self):
        #FIXME: Add logic to kill all devices
        return True
    