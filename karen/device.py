import logging
import threading 
import time
import os
import socket 
import ssl
import uuid
from urllib.parse import urljoin

from .shared import threaded, KHTTPRequestHandler, KJSONRequest, sendJSONRequest
from pickle import NONE

class DeviceContainer:
    """
    Karen's Client Device Manager.
    
    The sole purpose of the device container is to facilitate communication between one or more input/output devices and the brain.
    The device container allows for multiple client devices to be attached to a single communication vehicle.
    This minimizes the overhead on the device to send its collected content to the brain.
    """
    
    def __init__(self, tcp_port=8081, hostname="localhost", ssl_cert_file=None, ssl_key_file=None, brain_url="http://localhost:8080", friendlyName=None):
        """
        Device Container Initialization
        
        Args:
            tcp_port (int): The TCP port on which the brain's TCP server will listen for incoming connections
            hostname (str): The network hostname or IP address for the TCP server daemon
            ssl_cert_file (str): The path and file name of the SSL certificate (.crt) for secure communications
            ssl_key_file (str): The path and file name of the SSL private key (.key or .pem) for secure communications
            brain_url (str):  The URL of the brain device.
            friendlyName (str): The user-defined named for this device (a.k.a. "living room"). (optional)
        
        Both the ssl_cert_file and ssl_key_file must be present in order for SSL to be leveraged.
        """

        self._lock = threading.Lock()   # Lock for daemon processes
        self._socket = None             # Socket object (where the listener lives)
        self._thread = None             # Thread object for TCP Server (Should be non-blocking)
        self._deviceThread = None       # Thread object for device checks (runs every 5 seconds to confirm devices are active)
        self.isRunning = False         # Flag used to indicate if TCP server should be running
        self._threadPool = []           # List of running threads (for incoming TCP requests)
        
        self._handlers = {}             # Handlers to be called for incoming command requests (e.g. { "KILL": kill_function }
        
        self.objects = {}               # Input/Output devices as objects
        
        self.logger = logging.getLogger("CONTAINER")
        self.httplogger = logging.getLogger("HTTP")
        
        self.name = friendlyName
        
        # TCP Command Interface
        self.tcp_port = tcp_port if tcp_port is not None else 8080           # TCP Port for listener.
        self.hostname = hostname if hostname is not None else "localhost"    # TCP Hostname
        self.use_http = True
        self.keyfile=ssl_cert_file
        self.certfile=ssl_key_file

        self.use_http = False if self.keyfile is not None and self.certfile is not None else True
        
        self.brain_url = brain_url      # URL for the brain (REQUIRED)

        self.isOffline = None 
        self.webgui_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "web")
                        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.
                                        # NOTE:  This does not mean only 5 clients can exist.  This is how many
                                        #        inbound TCP connections the server will accept at the same time.
                                        #        A client will not hold open the connection so this should scale
                                        #        to be quite large before becoming a problem.
        
        self.my_url = "http://"
        if not self.use_http:
            self.my_url = "https://"
        self.my_url = self.my_url + str(self.hostname) + ":" + str(self.tcp_port)
    
    def _sendRequest(self, path, payLoad):
        """
        Sends a request to the brain
        
        Args:
            path (str):  The path of the request (e.g. "control" or "data").
            payLoad (object):  The object to be converted to JSON and sent in the body of the request.
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        url = urljoin(self.brain_url, path)
        ret, msg = sendJSONRequest(url, payLoad)
        return ret
    
    def registerWithBrain(self):
        """
        Sends a registration request to the brain for this client container indicating what devices it represents.
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        self.logger.debug("Registration STARTED")
        
        data = {}
        for deviceType in self.objects:
            #friendlyNames = []
            #for item in self.objects[deviceType]:
            #    if item["friendlyName"] is not None:
            #        friendlyNames.append(item["friendlyName"])
                    
            #data[deviceType] = { "count": len(self.objects[deviceType]), "names": friendlyNames }
            data[deviceType] = []
            for i, item in enumerate(self.objects[deviceType]):
                data[deviceType].append({ "uuid": item["uuid"], "active": item["device"].isRunning, "name": item["friendlyName"]})
            
        result = self._sendRequest("register", { "port": self.tcp_port, "useHttp": self.use_http, "name": self.name, "devices": data })
        if result:
            self.logger.info("Registration COMPLETE")
        else:
            self.logger.error("Registration FAILED")
                
        return result
    
    @threaded
    def _acceptConnection(self, conn, address):
        """
        Accepts inbound TCP connections, parses request, and calls appropriate handler function
        
        Args:
            conn (socket): The TCP socket for the connection
            address (tuple):  The originating IP address and port for the incoming request e.g. (192.168.0.139, 59209).
            
        Returns:
            (thread):  The thread for the active request connection
        """
        
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

            if r.command == "OPTIONS":
                print(r.headers) 
                headers = str(r.headers).split("\n") 
                includeHeaders = []
                for line in headers:
                    if line.startswith("Access-Control-Request-Headers: "):
                        line = line.replace("Access-Control-Request-Headers: ","").strip().lower()
                        if "content-type" in line:
                            includeHeaders.append("Content-Type")
                        if "content-length" in line:
                            includeHeaders.append("Content-Length")
                        
                if len(includeHeaders) == 0:
                    includeHeaders = None
                
                print(includeHeaders)
                return req.sendResponse(False, "OK", headers=includeHeaders)
            
            if (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
                return self._processCommandRequest(req)
            
            elif (len(path) == 7 and path == "/status") or (len(path) > 7 and path[:8] == "/status/"):
                return self._processStatusRequest(req)
            else:
                return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
        except:
            raise
            req = KJSONRequest(self, conn, None, None)
            return req.sendResponse(True, "invalid request", httpStatusCode=500, httpStatusMessage="Internal Server Error")
    
    @threaded
    def _tcpServer(self):
        """
        Internal function that creates the listener socket and hands off incoming connections to other functions.
            
        Returns:
            (thread):  The thread for the container's TCP server
        """
        
        self.isRunning = True 
                
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

        while self.isRunning:

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
    
    def _processStatusRequest(self, jsonRequest):
        """
        Processes an inbound status request.  Generally returns a summary of connected devices and friendly names.
        
        Args:
            jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
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

    def _processCommandRequest(self, jsonRequest):
        """
        Processes an inbound data request.  Parses the command and calls the respective command handler.
        
        Args:
            jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        my_cmd = str(jsonRequest.payload["command"]).upper().strip()
        if my_cmd in self._handlers:
            return self._handlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid command.")
    
    def start(self, useThreads=True, autoRegister=True, autoStartDevices=False):
        """
        Starts the client TCP daemon, optionally using threads.
        
        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
            autoRegister (bool):  Indicates if the client should automatically register with the brain
            autoStartDevices (bool):  Indicates if this call should also start any stopped or not started input/output devices.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        if self.isRunning:
            return True 

        if autoRegister:
            self.registerWithBrain()
        
        self._thread = self._tcpServer()
        self.logger.info("Started @ "+ str(self.my_url))
        
        if autoStartDevices:
            for deviceType in self.objects:
                for item in self.objects[deviceType]:
                    if not item["device"].isRunning:
                        item["device"].start()
                        
        if not useThreads:
            self._thread.join()
            self._deviceThread.join()

        return True

    def wait(self, seconds=0):
        """
        Waits for any active servers to complete before closing
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

        #if not self.isRunning:
        #    return True 
                
        if seconds > 0:
            self.logger.info("Shutting down in "+str(seconds)+" second(s).")
            for i in range(0,seconds):
                if self.isRunning:
                    time.sleep(1)
            
            if self.isRunning and self._thread is not None:
                self.stop()
        
        
        if self._thread is not None:
            self._thread.join()
            
        if self._deviceThread is not None:
            self._deviceThread.join()
        
        self.stopDevices()
        
        return True

    def stop(self):
        """
        Stops the client TCP server daemon.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        if not self.isRunning:
            return True 
        
        self.isRunning = False 
        
        i = len(self._threadPool) - 1
        while i >= 0:
            try:
                self._threadPool[i].join()
            except:
                pass
                
            i = i - 1
        
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
        """
        Stops all connected input/output devices.
        
        Args:
            deviceType (str):  The type of device to stop (e.g. "karen.listener.Listener"). (optional)
            removeDevices (bool):  Indicates if the devices should be removed once stopped. (optional)
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        for ldeviceType in self.objects:
            if deviceType is None or deviceType == ldeviceType:
                for item in self.objects[ldeviceType]:
                    if item["device"].isRunning:
                        item["device"].stop()
            
                if removeDevices:
                    self.objects[ldeviceType] = []
                
        return True
    
    def addDevice(self, deviceType, obj, friendlyName=None, id=None, autoStart=True, autoRegister=True):
        """
        Adds a new input/output device and optionally starts it and registers it with the brain.
        
        Args:
            deviceType (str):  The type of the device being added (e.g. "karen.listener.Listener").
            obj (object):  The instantiated class object of the input/output device.
            friendlyName (str):  The friendly name of the device (e.g. "living room"). (optional)
            id (str):  The Unique ID of this device.  If not set then will default to uuid.uuid4().
            autoStart (bool):  Indicates if this call should call the start() method on input/output device.
            autoRegister (bool):  Indicates if the client should automatically register with the brain
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        deviceType = str(deviceType).strip()
        if deviceType not in self.objects:
            self.objects[deviceType] = []
        
        self.objects[deviceType].append({ "device": obj, "friendlyName": friendlyName, "uuid": str(uuid.uuid4()) if id is None else str(id) })
        self.logger.info("Added " + str(deviceType))

        if autoStart:
            if not obj.isRunning:
                self.logger.debug("Requesting start for " + str(deviceType))
                obj.start()
                self.logger.debug("Start request completed for " + str(deviceType))

        if self.isRunning and autoRegister:
            self.registerWithBrain()
            
        return True 
    
    def setHandler(self, handlerType, handlerCallback):
        """
        Sets the handler to be used for incoming control requests
        
        Args:
            handlerType (str):  The type of incoming control request to handle (e.g. "KILL").
            handlerCallback (function):  The function to call when the control request matches the handler type
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        self._handlers[handlerType] = handlerCallback
        return True
    
    def callbackHandler(self, inType, data):
        """
        The target of all input/output devices.  Sends collected data to the brain.  Posts request to "/data".
        
        Args:
            inType (str):  The type of data collected (e.g. "AUDIO_INPUT").
            data (object):  The object to be converted to JSON and sent to the brain in the body of the message.
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        jsonData = { "type": inType, "data": data }
        result = self._sendRequest("/data", jsonData)
        return result
    
class Device:
    """
    EXAMPLE: Input/Output Device
    
    This can be inherited by devices and overridden as necessary.
    """
    
    def __init__(self, callback=None):
        """
        EXAMPLE: Input/Output Device Initialization
        
        Args:
            callback (function):  The method to call when new data is collected.
        """
        
        self.type == "DEVICE_TYPE"
        self.uuid = str(uuid.uuid4())
        self.name = ""
        self.isRunning = False
        pass 
    
    def start(self, useThreads=True):
        """
        EXAMPLE: Starts the input/output device
        
        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
        
        Returns:
            (bool):  True on success else will raise an exception.
        """

        self.isRunning = True
        return True 
    
    def wait(self, seconds=0):
        """
        EXAMPLE: Waits for specified seconds to complete before closing
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        #TODO: Wait specified time and then...
        self.stop()
        return True
    
    def stop(self):
        """
        EXAMPLE: Stops the device.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        self.isRunning = False
        return True