'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Device Container for assembling input/output devices
'''

import logging
import threading 
import time
import os
import socket 
import ssl
from urllib.parse import urljoin

from .shared import threaded, KHTTPRequestHandler, KJSONRequest, sendJSONRequest

class DeviceContainer:
    def __init__(self, tcp_port=8081, hostname="localhost", ssl_cert_file=None, ssl_key_file=None, brain_url="http://localhost:8080"):

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
        self.tcp_port = tcp_port if tcp_port is not None else 8080           # TCP Port for listener.
        self.hostname = hostname if hostname is not None else "localhost"    # TCP Hostname
        self.use_http = True
        self.keyfile=ssl_cert_file
        self.certfile=ssl_key_file

        self.use_http = False if self.keyfile is not None and self.certfile is not None else True
        
        self.brain_url = brain_url

        self.isOffline = None 
        self.webgui_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "web")
                        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.
        
        self.my_url = "http://"
        if not self.use_http:
            self.my_url = "https://"
        self.my_url = self.my_url + str(self.hostname) + ":" + str(self.tcp_port)
        
        #self.setHandler("START_LISTENER", handleStartStopListenerCommand)
        #self.setHandler("STOP_LISTENER", handleStartStopListenerCommand)
        #self.setHandler("KILL", handleKillCommand)
        #self.setHandler("AUDIO_OUT_START", handleAudioOutCommand)
        #self.setHandler("AUDIO_OUT_END", handleAudioOutCommand)
        #self.setHandler("SAY", handleSayCommand)
    
    def _sendRequest(self, path, payLoad):
        url = urljoin(self.brain_url, path)
        ret, msg = sendJSONRequest(url, payLoad)
        return ret
    
    def _registerWithBrain(self):
        self.logger.debug("Registration STARTED")
        
        data = {}
        for deviceType in self.objects:
            friendlyNames = []
            for item in self.objects[deviceType]:
                if item["friendlyName"] is not None:
                    friendlyNames.append(item["friendlyName"])
                    
            data[deviceType] = { "count": len(self.objects[deviceType]), "names": friendlyNames }
            
        result = self._sendRequest("register", { "port": self.tcp_port, "useHttp": self.use_http, "devices": data })
        if result:
            self.logger.info("Registration COMPLETE")
        else:
            self.logger.error("Registration FAILED")
                
        return result
    
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
                data = {}
                for deviceType in self.objects:
                    friendlyNames = []
                    for item in self.objects[deviceType]:
                        if item["friendlyName"] is not None:
                            friendlyNames.append(item["friendlyName"])
                            
                    data[deviceType] = { "count": len(self.objects[deviceType]), "names": friendlyNames }
                        
                return jsonRequest.sendResponse(message="Device list completed.", data=data)
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
                    if not item["device"]._isRunning:
                        item["device"].start()
                        
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
                    if item["device"]._isRunning:
                        item["device"].stop()
            
                if removeDevices:
                    self.objects[ldeviceType] = []
                
        return True
    
    def addDevice(self, deviceType, obj, friendlyName=None, autoStart=True, autoRegister=True):
        deviceType = str(deviceType).strip()
        if deviceType not in self.objects:
            self.objects[deviceType] = []
        
        self.objects[deviceType].append({ "device": obj, "friendlyName": friendlyName })
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
        return result
    
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