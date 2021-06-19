import logging
import time
import socket
import threading
import ssl
import json 
import os
from urllib.parse import urljoin

from .shared import threaded, sendHTTPResponse, KHTTPRequestHandler, KJSONRequest, sendJSONRequest
from .skillmanager import SkillManager
from . import __version__, __app_name__

class Brain(object):
    """
    Karen's input/response module.
    
    The Brain leverages a JSON-based TCP server for communication with its input/output devices.
    The primary purpose of the brain is to accept data and send control commands to the devices to take action.
    """
    
    def __init__(self, tcp_port=8080, hostname="localhost", ssl_cert_file=None, ssl_key_file=None, skill_folder=None):
        """
        Brain Server Initialization
        
        Args:
            tcp_port (int): The TCP port on which the brain's TCP server will listen for incoming connections
            hostname (str): The network hostname or IP address for the TCP server daemon
            ssl_cert_file (str): The path and file name of the SSL certificate (.crt) for secure communications
            ssl_key_file (str): The path and file name of the SSL private key (.key or .pem) for secure communications
            skill_folder (str): The path in which the skill modules are located.
        
        Both the ssl_cert_file and ssl_key_file must be present in order for SSL to be leveraged.
        """
        
        self._lock = threading.Lock()   # Lock for daemon processes
        self._socket = None             # Socket object (where the listener lives)
        self._thread = None             # Thread object for TCP Server (Should be non-blocking)
        self._deviceThread = None       # Thread object for device checks (runs every 5 seconds to confirm devices are active)
        self._isRunning = False         # Flag used to indicate if TCP server should be running
        self._threadPool = []           # List of running threads (for incoming TCP requests)
        
        self.skill_manager = SkillManager(self, skill_folder)
        self.skill_manager.initialize()
        
        self._callbacks = {}            # Internall callback storage.  Current example is "ask" function
        self._actionCommands = []       # List of the command handler string values for use in the web gui (e.g. "KILL")
        self._dataCommands = []         # List of the data handler string values for use in the web gui (e.g. "AUDIO_INPUT")
        
        self._data = {}                 # General storage object for inbound data (see Brain.AddData())
        self.clients = []               # Client Devices each in the form of { "url": "http://", "active": true }
        self._handlers = {}             # Command Handlers by their caller e.g. { "KILL": handler_function }
        self._dataHandlers = {}         # Data Handlers by their caller e.g. { "AUDIO_INPUT": handler_function }
        
        self.logger = logging.getLogger("BRAIN")
        self.httplogger = logging.getLogger("HTTP")
        
        # TCP Command Interface
        self.tcp_port = tcp_port if tcp_port is not None else 8080           # TCP Port for listener.
        self.hostname = hostname if hostname is not None else "localhost"    # TCP Hostname
        self.use_http = True
        self.keyfile=ssl_cert_file
        self.certfile=ssl_key_file

        self.use_http = False if self.keyfile is not None and self.certfile is not None else True
        
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
        
    @threaded
    def _acceptConnection(self, conn, address):
        """
        Accepts inbound TCP connections, parses request, and calls appropriate handler function
        
        Args:
            conn (socket): The TCP socket for the connection
            address (tuple):  The originating IP address and port for the incoming request e.g. (192.168.0.139, 59209).
            
        Returns:
            (thread):  The thread for the request's connection
        """
        
        try:
            # Parse the inbound request
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
                return self._processCommandRequest(req)
            
            elif (len(path) == 5 and path == "/data") or (len(path) > 5 and path[:6] == "/data/"):
                return self._processDataRequest(req)
            
            elif (len(path) == 7 and path == "/status") or (len(path) > 7 and path[:8] == "/status/"):
                return self._processStatusRequest(req)

            elif (len(path) == 9 and path == "/register") or (len(path) > 9 and path[:10] == "/register/"):
                return self._registerClient(address, req)
            
            elif (len(path) == 7 and path == "/webgui") or (len(path) > 7 and path[:8] == "/webgui/"):
                return self._processFileRequest(conn, path, payload)
            
            elif path == "/favicon.ico" or path == "/webgui/favicon.ico":
                response_type = "image/svg+xml"
                myfile = os.path.join(self.webgui_path, "favicon.svg")
                with open(myfile, mode='r') as f:
                    response_body = f.read()
                    
                return sendHTTPResponse(conn, responseType=response_type, responseBody=response_body)
            
            else:
                return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
        except Exception as e:
            req = KJSONRequest(self, conn, None, None)
            return req.sendResponse(True, "Invalid request", httpStatusCode=404, httpStatusMessage="Not Found")
    
    @threaded
    def _tcpServer(self):
        """
        Internal function that creates the listener socket and hands off incoming connections to other functions.
        
        Returns:
            (thread):  The thread for the TCP Server daemon

        """
        
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
            
    def _registerClient(self, address, jsonRequest):
        """
        Receives inbound registration requests and adds clients to internal list of active clients.
        
        Args:
            address (tuple): The originating IP address and port for the incoming request e.g. (192.168.0.139, 59209).
            jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
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
        """
        Routine to add data to the brain.  Stores the most recently added 50 items per type.
        
        Args:
            inType (str): The data type under which to save the data
            inData (object):  The data in which to be saved.  The specific type (str, dict, list, etc.) is dependent on the type of data being saved and controlled by the caller.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        if inType is not None and inType not in self._data:
            self._data[inType] = []
            
        self._data[inType].insert(0, { "data": inData, "time": time.time() } )
        if len(self._data[inType]) > 50:
            self._data[inType].pop()
            
        return True
    
    def setHandler(self, handlerType, handlerCallback, enableWebControl=True, friendlyName=None):
        """
        Sets the handler to be used for incoming control requests
        
        Args:
            handlerType (str):  The type of incoming control request to handle (e.g. "KILL").
            handlerCallback (function):  The function to call when the control request matches the handler type
            enableWebControl (bool):  Indicates if the handler type should be listed in the web gui as a button
            friendlyName (str):  The user-readable name of the control. (optional)
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
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
        """
        Sets the handler to be used for incoming data requests
        
        Args:
            handlerType (str):  The type of incoming control request to handle (e.g. "AUDIO_INPUT").
            handlerCallback (function):  The function to call when the control request matches the handler type
            enableWebControl (bool):  Indicates if the handler type should be listed in the web gui as an option in the drop down
            friendlyName (str):  The user-readable name of the control. (optional)
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

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
    
    def sendRequestToDevices(self, path, payload, inType=None, friendlyName=None):
        """
        Sends a JSON request to one or more client devices.
        
        Args:
            path (str):  relative path to call (e.g. "control" or "data").
            payload (object):  Object to be converted to JSON and sent in the body of the request
            inType (str):  The type of device to deliver the request to (e.g. "karen.listener.Listener").  This will limit the request to only clients with the specified type of device attached.  (optional) 
            friendlyName (str):  The friendly name of the client device (e.g. "living room").  This will limit the request to only clients that a device (of the specified type) with that friendly name.  (optional)
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        ret = True 
        
        for device in self.clients:
            
            url = device["url"] if "url" in device else None
            if url is None:
                continue
            
            active = device["active"] if "active" in device else False
            if not active:
                continue
            
            if inType is not None and (inType not in device["devices"] or device["devices"][inType]["count"] == 0):
                continue
            
            if friendlyName is not None:
                if inType is not None:
                    if friendlyName not in device["devices"][inType]["names"]:
                        continue 
                else:
                    bFound = False
                    for devType in device["devices"]:
                        if friendlyName in device["devices"][devType]["names"]:
                            bFound = True
                            break
                        
                    if not bFound:
                        continue
                    
            tgtPath = urljoin(url, path)

            ret, msg = sendJSONRequest(tgtPath, payload)
            if not ret:
                self.logger.error("Request failed to " + tgtPath)
                self.logger.debug(json.dumps(payload))
                ret = False 
        
        return ret
    
    def _processStatusRequest(self, jsonRequest):
        """
        Processes an inbound status request.  Generally returns a list of connected devices and their relative details.
        
        Args:
            jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        if jsonRequest.path == "/status/devices":
            if "command" in jsonRequest.payload and str(jsonRequest.payload["command"]).lower() == "get-all-current":
                return jsonRequest.sendResponse(False, "Device list completed.", data=self.clients )
            else:
                return jsonRequest.sendResponse(True, "Invalid command.", http_status_code=500, http_status_message="Internal Server Error")
        
        return jsonRequest.sendResponse(False, "Brain is online.")
        
    def _processFileRequest(self, conn, path, payload):
        """
        Accepts an inbound request for a file.  Leveraged by the Web GUI to server the HTML pages.
        
        Args:
            conn (socket):  The incoming socket connection for the request
            path (str):  The path of the incoming request (e.g. "/webgui/index.html").
            payload (object):  The content body of the request
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
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
    
    def _processDataRequest(self, jsonRequest):
        """
        Processes an inbound data request.  Parses the command and calls the respective data handler.
        
        Args:
            jsonRequest (karen.shared.KJSONRequest): Object containing the inbound JSON request
            
        Returns:
            (bool):  True on success or False on failure.
        """

        if "type" not in jsonRequest.payload or jsonRequest.payload["type"] is None:
            return jsonRequest.sendResponse(True, "Invalid data object.")
        
        my_cmd = str(jsonRequest.payload["type"])
        if my_cmd in self._dataHandlers:
            if self._dataHandlers[my_cmd] is None:
                return jsonRequest.sendResponse(False, "Complete.")

            return self._dataHandlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid data received.")

        return True
    
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
            if self._handlers[my_cmd] is None:
                return jsonRequest.sendResponse(False, "Command complete.")

            return self._handlers[my_cmd](jsonRequest)
        else:
            return jsonRequest.sendResponse(True, "Invalid command.")
    
    def ask(self, in_text, in_callback=None, timeout=0):
        """
        Method to create a action/response/reaction via voice interactions.
        
        Args:
            in_text (str):  The message to send to the speaker.
            in_callback (function):  The function to call when a response is received.
            timeout (int):  Number of seconds to wait on a response
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        ret = self.say(in_text)
        if in_callback is not None:
            self._callbacks["ask"] = { "function": in_callback, "timeout": timeout, "expires": time.time()+timeout }
        return True 
    
    def say(self, text):
        """
        Method to send a message to the speaker to be spoken audibly.
        
        Args:
            text (str):  The message to send to the speaker.
            
        Returns:
            (bool):  True on success or False on failure.
        """
        
        speaker = None
        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "karen.speaker.Speaker" in item["devices"] and item["devices"]["karen.speaker.Speaker"]["count"] > 0:
                    speaker = item["url"]
                    break
        
        if speaker is None:
            self.logger.warning("SAY: No speaker identified")
            return False
        
        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "karen.listener.Listener" in item["devices"] and item["devices"]["karen.listener.Listener"]["count"] > 0:
                    sendJSONRequest(urljoin(item["url"],"control"), { "command": "AUDIO_OUT_START" })

        sendJSONRequest(urljoin(speaker,"control"), { "command": "SAY", "data": str(text) })

        for item in self.clients:
            if "active" in item and item["active"]:
                if "devices" in item and "karen.listener.Listener" in item["devices"] and item["devices"]["karen.listener.Listener"]["count"] > 0:
                    sendJSONRequest(urljoin(item["url"],"control"), { "command": "AUDIO_OUT_END" })
            
        return True
    
    def start(self, useThreads=True):
        """
        Starts the brain TCP daemon, optionally using threads.
        
        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

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
        """
        Waits for any active servers to complete before closing
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

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
        
        return True

    def stop(self):
        """
        Stops the brain TCP server daemon.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
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
        
        self.logger.info("Stopped")
            
        return True
