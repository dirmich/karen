import logging
import threading 
import time
import os
import sys
import traceback
import socket 
import ssl
import urllib3
import requests
from urllib.parse import urljoin
import json

from .shared import threaded, KHTTPRequestHandler, KJSONRequest
from . import __version__, __app_name__

def handleKillCommand(jsonRequest):
    jsonRequest.container.logger.debug("KILL received.")
    jsonRequest.sendResponse(False, "Device container is shutting down")
    return jsonRequest.container.stop()

def handleStartStopListenerCommand(jsonRequest):

    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    if "listener" in jsonRequest.container.objects:
        for item in jsonRequest.container.objects["listener"]:
            if my_cmd == "START_LISTENER":
                item.start()
            elif my_cmd == "STOP_LISTENER":
                item.stop()
        
    return jsonRequest.sendResponse(False, "Command completed.") 

def handleAudioOutCommand(jsonRequest):
    
    my_cmd = str(jsonRequest.payload["command"]).upper()
    jsonRequest.container.logger.debug(my_cmd + " received.")

    if my_cmd == "AUDIO_OUT_START":    
        if "listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["listener"]:
                item.logger.debug("AUDIO_OUT_START")
                item._isAudioOut = True
                
        return jsonRequest.sendResponse(False, "Pausing Listener during speech utterence.")
    elif my_cmd == "AUDIO_OUT_END":    
        if "listener" in jsonRequest.container.objects:
            for item in jsonRequest.container.objects["listener"]:
                item.logger.debug("AUDIO_OUT_END")
                item._isAudioOut = False
                
        return jsonRequest.sendResponse(False, "Engaging Listener after speech utterence.")
    else:
        return jsonRequest.sendResponse(True, "Invalid command data.")
    
def handleSayCommand(jsonRequest):
    #SAY command is not relayed to the brain.  It must be received by the brain or a speaker instance directly.
    
    if "data" not in jsonRequest.payload or jsonRequest.payload["data"] is None:
        jsonRequest.container.logger.error("Invalid payload for SAY command detected")
        return jsonRequest.sendResponse(True, "Invalid payload for SAY command detected.") 
    
    if "speaker" in jsonRequest.container.objects:
        # First we try to send to active speakers physically connected to the same instance
        for item in jsonRequest.container.objects["speaker"]:
            item.say(str(jsonRequest.payload["data"]))
            return jsonRequest.sendResponse(False, "Say command completed.") 

    return jsonRequest.sendResponse(True, "Speaker not available.") 

class DeviceContainer:
    def __init__(self, **kwargs):

        self._lock = threading.Lock()   # Lock for daemon processes
        self._socket = None             # Socket object (where the listener lives)
        self._thread = None             # Thread object for TCP Server (Should be non-blocking)
        self._deviceThread = None       # Thread object for device checks (runs every 5 seconds to confirm devices are active)
        self._isRunning = False         # Flag used to indicate if TCP server should be running
        self._threadPool = []           # List of running threads (for incoming TCP requests)
        
        self._data = {}
        
        self._handlers = {}
        
        self.objects = {}
        self.brain = None
        
        self.logger = logging.getLogger("CONTAINER")
        self.httplogger = logging.getLogger("HTTP")
        
        # TCP Command Interface
        self.tcp_port = 8081            # TCP Port for listener.
        self.hostname = "localhost"     # TCP Hostname
        self.use_http = True
        self.keyfile=None
        self.certfile=None
        
        self.brain_url = "http://localhost:8080"

        self.isOffline = None 
        self.webgui_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "web")
                        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.
        
        self.my_url = "http://"
        if not self.use_http:
            self.my_url = "https://"
        self.my_url = self.my_url + str(self.hostname) + ":" + str(self.tcp_port)
        
        self.setHandler("START_LISTENER", handleStartStopListenerCommand)
        self.setHandler("STOP_LISTENER", handleStartStopListenerCommand)
        self.setHandler("KILL", handleKillCommand)
        self.setHandler("AUDIO_OUT_START", handleAudioOutCommand)
        self.setHandler("AUDIO_OUT_END", handleAudioOutCommand)
        self.setHandler("SAY", handleSayCommand)
    
    def _sendRequest(self, path, payLoad):
        
        url = urljoin(self.brain_url, path)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
        result = { "error": True, "message": None }

        try:    
            #url = 'https://localhost:8031/requests'
            #mydata = {'somekey': 'somevalue'}
            
            headers = { "Content-Type": "application/json" }
            request_body = json.dumps(payLoad)
            
            res = requests.post(url, data=request_body, headers=headers, verify=False)
    
            if res.ok:
                try:
                    res_obj = json.loads(res.text)
                    if "error" in res_obj and "message" in res_obj:
                        result = res_obj
                except:
                    self.httplogger.error("Unable to parse response from " + str(url) + "")
                    self.httplogger.debug(str(res.text))
                    pass
            else:
                self.httplogger.error("Request failed for " + str(url) + "")
                self.httplogger.debug(str(res.text))
        except requests.exceptions.ConnectionError:
            self.httplogger.error("Connection Failed: " + url)
        except:
            self.httplogger.error(str(sys.exc_info()[0]))
            self.httplogger.error(str(traceback.format_exc()))
            
        return result
    
    def _registerWithBrain(self):
        self.logger.debug("Registration STARTED")
        
        data = {}
        for deviceType in self.objects:
            data[deviceType] = len(self.objects[deviceType])
            
        result = self._sendRequest("register", { "port": self.tcp_port, "useHttp": self.use_http, "devices": data })
        if result["error"] == False:
            self.logger.info("Registration COMPLETE")
        else:
            self.logger.error("Registration FAILED")
            if result["message"] is not None:
                self.logger.debug(str(result["message"]))
                
        return not result["error"]
    
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
            
            self.httplogger.debug("CONTAINER (" + str(address[0]) + ") " + str(r.command) + " " + str(path))
            
            req = KJSONRequest(self, conn, path, payload)
            if (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
                return self.processCommandRequest(req)
            
            elif (len(path) == 7 and path == "/status") or (len(path) > 7 and path[:8] == "/status/"):
                return self.processStatusRequest(req)
            else:
                return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
        except:
            req = KJSONRequest(self, conn, None, None)
            return req.sendResponse(True, "invalid request", httpStatusCode=500, httpStatusMessage="Internal Server Error")
    
    @threaded
    def _tcpServer(self):
        
        self._isRunning = True 
                
        self._lock.acquire()

        self._socket = socket.socket()
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.hostname, self.tcp_port))
        self._socket.listen(self.tcp_clients)
        
        if self.use_http == False:
            self.httplogger.debug("SSL - Enabled")
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
                
                self.logger.info("Ctrl+C detected.  Shutting down.")
                self.stop()  # Stop() is all we need to cleanly shutdown.  Will call child class's method first.
                
                return True # Nice and neat closing
                
            except (OSError): # Occurs when we force close the listener on stop()
                
                pass    # this error will be raised on occasion depending on how the TCP socket is stopped
                        # so we put a simple "ignore" here so it doesn't fuss too much.
        
        return True
    
    def processStatusRequest(self, jsonRequest):
        # TBD
        if jsonRequest.path == "/status/devices":
            if "command" in jsonRequest.payload and str(jsonRequest.payload["command"]).lower() == "get-all-current":
                #FIXME: Object List is not accurate
                devices = {}
                for deviceType in self.objects:
                    devices[deviceType] = len(self.objects[deviceType])
                        
                return jsonRequest.sendResponse(message="Device list completed.", data=self.objects)
            else:
                return jsonRequest.sendResponse(True, "Invalid command.", http_status_code=500, http_status_message="Internal Server Error")
        
        return jsonRequest.sendResponse(message="Device is active.")

    def processCommandRequest(self, jsonRequest):
        my_cmd = str(jsonRequest.payload["command"]).upper().strip()
        if my_cmd in self._handlers:
            return self._handlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid command.")
    
    def start(self, useThreads=True, autoRegister=True, autoStartDevices=False):

        if self._isRunning:
            return True 

        if autoRegister:
            self._registerWithBrain()
        
        self._thread = self._tcpServer()
        self.logger.info("Started @ "+ str(self.my_url))
        
        if autoStartDevices:
            for deviceType in self.objects:
                for item in self.objects[deviceType]:
                    if not item._isRunning:
                        item.start()
                        
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

    def stop(self):
        
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
            
        self.stopDevices()
        
        self.logger.info("Stopped @ "+ str(self.my_url))
            
        return True
    
    def stopDevices(self, deviceType=None, removeDevices=False):
        
        for ldeviceType in self.objects:
            if deviceType is None or deviceType == ldeviceType:
                for item in self.objects[ldeviceType]:
                    if item._isRunning:
                        item.stop()
            
                if removeDevices:
                    self.objects[ldeviceType] = []
                
        return True
    
    def addDevice(self, deviceType, obj, autoStart=True, autoRegister=True):
        deviceType = str(deviceType).strip().lower()
        if deviceType not in self.objects:
            self.objects[deviceType] = []
        
        self.objects[deviceType].append(obj)
        self.logger.info("Added " + str(deviceType))

        if autoStart:
            if not obj._isRunning:
                self.logger.debug("Requesting start for " + str(deviceType))
                obj.start()
                self.logger.debug("Start request completed for " + str(deviceType))

        if self._isRunning and autoRegister:
            self._registerWithBrain()
            
        return True 
    
    def setHandler(self, handlerType, handlerCallback):
        self._handlers[handlerType] = handlerCallback
        return True
    
    def callbackHandler(self, type, data):
        jsonData = { "type": type, "data": data }
        result = self._sendRequest("/data", jsonData)
        return not result["error"]
    
class Device:
    def __init__(self):
        self.type == "DEVICE_TYPE"
        self._isRunning = False
        pass 
    
    def start(self):
        return True 
    
    def wait(self, seconds=0):
        return True
    
    def stop(self):
        return True