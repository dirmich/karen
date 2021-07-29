import os, logging, socket, ssl, time, uuid
from .shared import threaded, getIPAddress, KHTTPHandler, sendHTTPRequest
from urllib.parse import urljoin

class Container():
    def __init__(self, tcp_port=8080, hostname="", ssl_cert_file=None, ssl_key_file=None, brain_url=None, groupName=None):
        """
        Brain Server Initialization
        
        Args:
            tcp_port (int): The TCP port on which the TCP server will listen for incoming connections
            hostname (str): The network hostname or IP address for the TCP server daemon
            ssl_cert_file (str): The path and file name of the SSL certificate (.crt) for secure communications
            ssl_key_file (str): The path and file name of the SSL private key (.key or .pem) for secure communications
            brain_url (str): URL of brain device.
            groupName (str): Group or Room name for devices. (optional)
        
        Both the ssl_cert_file and ssl_key_file must be present in order for SSL to be leveraged.
        """
        
        from . import __app_name__, __version__
        self._version = __version__
        self._appName = __app_name__
        
        self.groupName = groupName
        
        self.app = None
        
        self.isBrain = False
        self.id = uuid.uuid4()
        self.type = "container"

        self._serverSocket = None             # Socket object (where the listener lives)
        self._serverThread = None             # Thread object for TCP Server (Should be non-blocking)
        self._threadPool = []           # List of running threads (for incoming TCP requests)
        
        self._isRunning = False         # Flag used to indicate if TCP server should be running
        
        self.logger = logging.getLogger("CONTAINER")
        
        # TCP Command Interface
        self.tcp_port = tcp_port if tcp_port is not None else 8080
        self.hostname = hostname if hostname is not None else "" 
        self.use_http = True
        self.keyfile=ssl_cert_file
        self.certfile=ssl_key_file

        self.use_http = False if self.keyfile is not None and self.certfile is not None else True
        
        self.isOffline = None 
                        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.
                                        # NOTE:  This does not mean only 5 clients can exist.  This is how many
                                        #        inbound TCP connections the server will accept at the same time.
                                        #        A client will not hold open the connection so this should scale
                                        #        to be quite large before becoming a problem.
        
        
        my_ip = getIPAddress() if self.hostname is None or self.hostname == "" else self.hostname
        self.my_url = "http://"
        if not self.use_http:
            self.my_url = "https://"
        self.my_url = self.my_url + str(my_ip if my_ip is not None and my_ip != "" else "localhost") + ":" + str(self.tcp_port)

        self.brain_url = brain_url
        if self.brain_url is None:
            self.brain_url = "http://localhost:8080"
        
        self.accepts = ["stop","stopDevices","status"]
        self.devices = {}
        
    def initialize(self):
        """
        Base initialization intended to be overridden in child classes.
        """
        self.addDevice(self.type, self, self.id, False, False)
        self.logger.debug("Container ["+str(self.type)+"] started with ID = " + str(self.id))
        return True
    
    def _purgeThreadPool(self):
        """
        Purges the thread pool of completed or dead threads
        """
        i = len(self._threadPool) - 1
        while i >= 0:
            try:
                if self._threadPool[i] is None or self._threadPool[i].isAlive() == False:
                    self._threadPool.pop(i)
            except:
                self._threadPool.pop(i)
                        
            i = i - 1
            
    def _waitForThreadPool(self):
        """
        Pauses and waits for all threads in threadpool to complete/join the calling thread
        """
        i = len(self._threadPool) - 1
        while i >= 0:
            try:
                if self._threadPool[i] is not None and self._threadPool[i].isAlive():
                    self._threadPool[i].abort()
            except:
                pass
                        
            i = i - 1
    
    @threaded
    def _tcpServer(self):
        """
        Internal function that creates the listener socket and hands off incoming connections to other functions.
        
        Returns:
            (thread):  The thread for the TCP Server daemon

        """
        self._isRunning = True 
                
        self._serverSocket = socket.socket()
        self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._serverSocket.bind((self.hostname, self.tcp_port))
        self._serverSocket.listen(self.tcp_clients)
        
        if self.use_http == False:
            self.logger.info("SSL Enabled.")
            self._serverSocket = ssl.wrap_socket(self._serverSocket, 
                                       keyfile=self.keyfile, 
                                       certfile=self.certfile,
                                       server_side=True)

        while self._isRunning:

            try:
                # Accept the new connection
                conn, address = self._serverSocket.accept()
                
                t = self._acceptConnection(conn, address)
                self._purgeThreadPool()
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
            req = KHTTPHandler(self, conn, address, conn.makefile(mode='b'))
            self.logger.debug("HTTP (" + str(address[0]) + ") " + str(req.command) + " " + str(req.path) + " [" + ("JSON" if req.isJSON else "") + "]")
            if req.validateRequest():
                #req.socket.send("HTTP/1.1 200 OK\nContent-Type: text/html\nContent-Length: 9\n\nNOT FOUND".encode())
                self._processRequest(req)
                
        except:
            raise
        
    def _getStatus(self):
        myDevices = {}
        for devId in self.devices:
            item = self.devices[devId]
            myDevices[devId] = { "id": devId, "type": item["type"], "accepts": item["accepts"], "active": True, "version": None, "groupName": self.groupName }
            
            try:
                myDevices[devId]["active"] = item["device"].isRunning()
            except:
                self.logger.error("Unable to parse local device status [running state].")
                pass

            try:
                myDevices[devId]["version"] = item["device"].version
            except Exception as e:
                self.logger.error("Unable to parse local device status [version].")
                pass
            
        return { self.my_url: myDevices }
    
    def _processRequest(self, httpRequest):
        try:
            if httpRequest.isFileRequest:
                return httpRequest.sendRedirect(self.brain_url)
        
            if (not httpRequest.isTypeRequest) and httpRequest.item in self.devices:
                result = eval("self.devices[httpRequest.item][\"device\"]."+httpRequest.action+"(httpRequest)")
                if not httpRequest.isResponseSent:
                    return httpRequest.sendJSON({ "error": False, "message": "Request completed successfully." })
                else:
                    return True 
                
            if httpRequest.isTypeRequest:
                
                for devId in self.devices:
                    item = self.devices[devId]
                    if httpRequest.item == "all" or item["type"] == httpRequest.item:
                        result = eval("self.devices[devId][\"device\"]."+httpRequest.action+"(httpRequest)")

                if not httpRequest.isResponseSent:
                    return httpRequest.sendJSON({ "error": False, "message": "Request completed successfully." })
                else:
                    return True 

        except AttributeError:
            return httpRequest.sendJSON({ "error": True, "message": "Request not supported." })
        except TypeError:
            return httpRequest.sendJSON({ "error": True, "message": "Request not supported." })
        except:
            raise
            return httpRequest.sendError()
        
        return httpRequest.sendError()
    
    def registerWithBrain(self):
        """
        Sends current container and child device plugin status to brain
        """
        
        ret = sendHTTPRequest(urljoin(self.brain_url,"brain/register"), jsonData=self._getStatus(), origin=self.my_url, groupName=self.groupName)[0]
        return ret
    
    def addDevice(self, type, device, id=None, autoStart=True, isPanel=False):
        """
        Add Device to list.
        
        Args:
            type (str):  The full class path to the device.
            device (obj):  The instance of the device
            id (str):  The string representation of a unique identifier.
            autoStart (bool): Automatically start the device
            
        Returns:
            (bool): True on success; False on failure.
        """
        type = str(type).strip()
        
        if id is None:
            id = uuid.uuid4()
        
        accepts = None
        try:
            accepts = device.accepts() # try as method
        except AttributeError:
            pass
        except TypeError:
            pass
        
        try:
            # Attempt to set the parent value on the device
            device.parent = self
            
        except:
            pass
        
        if accepts is None or not isinstance(accepts,list):
            try:
                accepts = device.accepts # try as variable
            except AttributeError:
                pass
            except TypeError:
                pass
            
        if accepts is None or not isinstance(accepts,list):
            accepts = []
            
        for i, item in enumerate(accepts):
            accepts[i] = str(item)
        
        self.devices[str(id)] = { 
                "type": str(type),
                "device": device,
                "accepts": accepts,
                "active": True,
                "isPanel": isPanel
            }
        
        try:
            if autoStart and "start" in accepts and not device.isRunning():
                self.logger.info("Starting Device: " + str(id) + " (" + str(type) + ")")
                self.devices[str(id)]["device"].start()
        except:
            pass
        
        if not self.isBrain:
            self.registerWithBrain()
        
        return True
    
    @property
    def version(self):
        """
        Returns the version of the service as a string value.
        """
        return self._version
    
    def isRunning(self):
        """
        Determine if device is running.
        
        Returns:
            (bool):  True if running, False if not running
        """
        return self._isRunning
        
    def start(self, useThreads=True):
        """
        Starts the container process, optionally using threads.
        
        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

        if self._isRunning:
            return True 

        self._thread = self._tcpServer()
        self.logger.info("Started @ "+ str(self.my_url))

        if not useThreads:
            self._thread.join()

        return True
    
    def status(self, httpRequest):
        """
        Collect status as a JSON object for container and all devices.
        
        Args:
            httpRequest (karen.shared.KHTTPHandler): Used to respond to status requests.
            
        Returns:
            (bool): True on success; False on Failure
        """
        
        return httpRequest.sendJSON(self._getStatus())
        
    def wait(self, seconds=0):
        """
        Waits for any active servers to complete before closing
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        if self.app is not None:
            self.app.exec_()
                
        if seconds > 0:
            self.logger.info("Shutting down in "+str(seconds)+" second(s).")
            for i in range(0,seconds):
                if self.isRunning(): # Checking to be sure nothing killed us while we wait.
                    time.sleep(1)
            
            if self.isRunning() and self._thread is not None:
                self.stop()
        
        if self._thread is not None:
            self._thread.join()
            
        return True

    def stop(self, httpRequest=None):
        """
        Stops the brain TCP server daemon.
        
        Args:
            httpRequest (KHTTPHandler):  Not used, but required for compatibility
            
        Returns:
            (bool):  True on success else will raise an exception.
        """

        if httpRequest is not None:
            httpRequest.sendJSON({ "error": False, "message": "All services are being shutdown." })

        if not self.isRunning():
            return True 
        
        self._isRunning = False  # Kills the listener loop 
        
        self._waitForThreadPool()
        
        if self._serverSocket is not None:
            try:
                self._serverSocket.shutdown(socket.SHUT_RDWR)
                self._serverSocket.close()
                self._serverSocket = None
            except:
                pass 
            
        self.stopDevices()
        
        if self.app is not None:
            self.app.quit()
        self.logger.info("Stopped")
            
        return True
    
    def stopDevices(self, httpRequest=None):
        """
        Stops all devices currently in container's list.
        
        Args:
            httpRequest (KHTTPHandler):  Not used, but required for compatibility
            
        Returns:
            (bool): True on success; False on failure
        """
        
        ret = True
        for item in self.devices:
            if item == str(self.id):
                continue 
            
            if "stop" in self.devices[item]["accepts"] and self.devices[item]["device"].isRunning():
                try:
                    self.devices[item]["device"].stop()
                except:
                    ret = False
                    
                try:
                    if self.devices[item]["isPanel"]:
                        self.devices[item]["device"].close()
                except:
                    pass
        
        return ret
    
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
        result = sendHTTPRequest(urljoin(self.brain_url,"/brain/collect"), jsonData=jsonData, origin=self.my_url, groupName=self.groupName)[0]
        return result 
    
class DeviceTemplate():
    def __init__(self,
            parent=None,
            callback=None):
        
        self.parent = parent
        self.callback = callback
        self._isRunning = False 
        
    @property
    def accepts(self):
        return ["start","stop"]
    
    @property
    def isRunning(self):
        return self._isRunning
    
    def start(self, httpRequest=None):
        self._isRunning = True
        return True
    
    def stop(self, httpRequest=None):
        self._isRunning = False
        return True