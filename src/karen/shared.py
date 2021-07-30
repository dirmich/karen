"""
Shared library of functions used throughout Karen's various modules
"""

import time 
import json
import threading 
from http.server import BaseHTTPRequestHandler 
from urllib.parse import parse_qs, urlparse, urlencode
from cgi import parse_header, parse_multipart
import socket
import logging 
import urllib3 
import requests 
import sys
import traceback 
import queue

def dayPart():
    """
    Returns the part of the day based on the system time based on generally acceptable breakpoints.
    
    Returns:
        (str):  The part of the day for the current moment (night, morning, evening, etc.).
    """
    
    # All we need is the current hour in 24-hr notation as an integer
    h = int(time.strftime("%H"))
    
    if (h < 4):
        # Before 4am is still night in my mind.
        return "night"
    elif (h < 12):
        # Before noon is morning
        return "morning"
    elif (h < 17):
        # After noon ends at 5pm
        return "afternoon"
    elif (h < 21):
        # Evening ends at 9pm
        return "evening"
    else:
        # Night fills in everything else (9pm to 4am)
        return "night"

def getIPAddress(iface=None):
    """
    Get IP address from specified interface.
    
    Args:
        iface (str): Interface name like 'eth0'.
        
    Returns:
        (str): IP address of interface.
    """
    
    import netifaces
    if iface is None:
        
        ifaces = netifaces.interfaces()
        for iface in ifaces:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    if addr["addr"] == "127.0.0.1":
                        continue
                    
                    return str(addr["addr"])
    
    else:
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                if addr["addr"] == "127.0.0.1":
                    continue
                
                return str(addr["addr"])

def threaded(fn):
    """
    Thread wrapper shortcut using @threaded prefix
    
    Args:
        fn (function):  The function to executed on a new thread.
        
    Returns:
        (thread):  New thread for executing function.
    """

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper

def getFileContents(fileName, mode="r"):
    """
    Gets the contents of a file in string or binary form.
    
    Args:
        fileName (str):  The name of the file
        mode (str):  The file open method; defaults to string reader.
        
    Returns:
        (object):  Contents of the file in string or binary form based on mode selection
    """

    if mode is None:
        mode = "r"
        
    if mode == "r":
        with open(fileName, encoding='utf-8') as fp:
            content = fp.read()

    else:
        with open(fileName, mode) as fp:
            content = fp.read()
    
    return content

class StreamingClient(object):
    """
    Streaming Media Client Class
    """
    
    def __init__(self):
        """
        Streaming Client Initialization.
        """
        self.streamBuffer = ""
        self.streamQueue = queue.Queue()
        self.streamThread = threading.Thread(target = self.stream)
        self.streamThread.daemon = True
        self.connected = True
        self.kill = False

        super(StreamingClient, self).__init__()
    
    def start(self):
        """
        Starts an independent thread for the streaming client to hand off data from the buffer to avoid blocking calls on new images.
        """
        self.streamThread.start()

    def transmit(self, data):
        """
        Overridden in inherited class, but would be used to transmit data to requestor.
        
        Args:
            data (byte):  Byte array to transmit
            
        Returns:
            (bool): True on success or False on failure
            
        """
        
        return True

    def stop(self):
        """
        Stops the streaming connection thread
        """
        self.kill = True
        self.connected = False

    def bufferStreamData(self, data):
        """
        Adds new data to the buffer for transmission to the requestor.
        
        Args:
            data (byte): Data to be saved to buffer
        """
        #use a thread-safe queue to ensure stream buffer is not modified while we're sending it
        self.streamQueue.put(data)

    def stream(self):
        """
        Thread runtime for reading data from the buffer and transmitting it to the client
        """
        
        while self.connected:
            #this call blocks if there's no data in the queue, avoiding the need for busy-waiting
            self.streamBuffer = self.streamQueue.get()
            
            #check if kill or connected state has changed after being blocked
            if (self.kill or not self.connected):
                self.stop()
                return

            self.transmit(self.streamBuffer)
                    

class TCPStreamingClient(StreamingClient):
    """
    TCP Streaming Media Client Class
    """
    
    def __init__(self, sock, includeHeader=True, includeBoundary=True):
        """
        TCP Streaming Client Initialization
        """
        super(TCPStreamingClient, self).__init__()
        self.logger = logging.getLogger("TCP_STREAM")
        self.sock = sock
        self.sock.settimeout(5)
        self.boundary = '--boundarydonotcross'
        self.includeHeader = includeHeader
        self.includeBoundary = includeBoundary
        
        self.logger.debug("Streaming client connected.")
        
        if includeHeader:
            self.sock.send(self.request_headers().encode())

    def request_headers(self):
        """
        Creates the headers for sending to the client on the beginning of the stream.
        
        Returns:
            (str):  Formatted HTTP headers for initial response to client
        """
        # Send first
        return "\n".join([
            "HTTP/1.1 200 OK",
            "Date: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z"),
            "Cache-Control: no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0",
            "Connection: close",
            "Content-Type: multipart/x-mixed-replace;boundary=\"" + self.boundary + "\"",
            "Expires: Mon, 1 Jan 2030 00:00:00 GMT",
            "Pragma: no-cache", 
            "Access-Control-Allow-Origin: *"]) + "\n\n" + self.boundary + "\n"
        
    def image_headers(self, data):
        """
        Generates headers for each frame of the MJPEG Stream.
        
        Args:
            data (byte):  Data from buffer that will be sent to client
            
        Returns:
            (str):  Formatted HTTP headers for individual image frame
        """
        
        # Send with each frame
        return "\n".join([
            "X-Timestamp: " + str(time.time()),
            "Content-Length: " + str(len(data)),
            "Content-Type: image/jpeg"
        ]) + "\n\n"
        
    def stop(self):
        """
        Stops the client connection and related sockets.
        """
        
        self.sock.close()
        super().stop()

    def transmit(self, data):
        """
        Sends data to client via TCP (HTTP) response.
        
        Args:
            data (byte): Data to be transmitted
        
        Returns:
            (bool): True on success
        """
        try:
            if self.includeHeader:
                self.sock.send(self.image_headers(data).encode())

            self.sock.send(data)
                
            if self.includeBoundary:
                self.sock.send(self.boundary.encode())

            return True
        except:
            self.connected = False
            self.sock.close()
            
        return True

def sendHTTPRequest(url, type="POST", params=None, jsonData=None, origin=None, groupName=None, isStream=True):
    
    #FIXME: Add context to request!
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    #url = 'https://localhost:8031/requests'
    #mydata = {'somekey': 'somevalue'}
    logger = logging.getLogger("HTTP")

    request_body = None
    headers = None
    
    try:
        if jsonData is not None:
            headers = { "Content-Type": "application/json" } #, "X-CLIENT-URL": context.clientURL, "X-BRAIN-URL": context.brainURL }
            request_body = json.dumps(jsonData)
        else:
            if params is not None and isinstance(params, dict):
                request_body = urlencode(params)
        
        if origin is not None:
            if headers is None:
                headers = {}
            
            headers["X-ORIGIN"] = str(origin)

        if groupName is not None:
            if headers is None:
                headers = {}
            
            headers["X-GROUP"] = str(groupName)
        
        if type == "GET": # Doesn't send request body
            res = requests.get(url, headers=headers, verify=False, stream=isStream)
        else:
            res = requests.post(url, data=request_body, headers=headers, verify=False, stream=isStream)
        
        ret_val = True
        if res.ok:
            try:
                if res.is_redirect or res.is_permanent_redirect:
                    return False # We don't support redirects
                
                ret_type, ret_param = parse_header(res.headers.get("content-type"))
                if ret_type == "application/json":
                    res_obj = res.json()
                    if "error" in res_obj and "message" in res_obj:
                        result = res_obj
                        ret_val = not result["error"]
                        
                    return ret_val, res.headers.get("content-type"), res.json() # returns as a dict
                
                # Else!
                if ret_type.startswith("text/"):
                    return True, ret_type, res.text # returns as a string
                elif ret_type == "multipart/x-mixed-replace":
                    return True, res.headers.get("content-type"), res # returns as request item
                else:
                    return True, res.headers.get("content-type"), res.content # returns as bytes
                        
            except:
                logger.error("Unable to parse response from " + str(url) + "")
                return False, res.headers.get("content-type"), res.text
        else:
            logger.error("Request failed for " + str(url) + "")
            return False, "text/html", "An error occurred in the HTTP request"

    except requests.exceptions.ConnectionError:
        logger.error("Connection Failed: " + url)
    except:
        logger.error(str(sys.exc_info()[0]))
        logger.error(str(traceback.format_exc()))

    return False, "text/html", "An error occurred in the HTTP request"

class KHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, container, sock=None, address=("localhost",0), raw_request=None, origin=None):
        
        self.container = container
        self.socket = sock
        self.address = address # tuple (ip, port)
        
        self.rfile = raw_request
        self.raw_requestline = self.rfile.readline() if raw_request is not None else None # first line of request e.g. "GET /index.html"
        self.error_code = None
        self.error_message = None
        self.path = None
        self.headers = {}

        self.isJSON = False
        self.JSON = None
        self.getVars = {}

        self.isFileRequest = False
        self.isDeviceRequest = False
        self.isBrainRequest = False
        self.isTypeRequest = False
        self.item = None
        self.action = None
        self.origin = origin
        self.groupName = None
        
        self.isResponseSent = False
        
        self.mimeTypes = {
                ".jpg": "image/jpeg",
                ".gif": "image/gif",
                ".png": "image/png",
                ".bmp": "image/bmp",
                ".svg": "image/svg+xml",
                ".mp3": "audio/mp3",
                ".mp4": "video/mp4"
            }
        
        if self.rfile is not None:
            self.parse_request()
        
        if self.path is not None:
            self.getVars = parse_qs(urlparse(self.path).query)
            self.path = urlparse(self.path).path
            
        if self.headers.get('content-type') is not None:
            ctype = parse_header(self.headers.get('content-type'))[0]
            if ctype == "application/json":
                self.isJSON = True
                
        if self.headers.get('x-origin') is not None:
            self.origin = parse_header(self.headers.get("x-origin"))[0]

        if self.origin is None or str(self.origin) == "": # If we aren't given one then we create an origin
            self.origin = self.container.my_url

        if self.headers.get('x-group') is not None:
            self.groupName = parse_header(self.headers.get("x-group"))[0]
                
    def sendRedirect(self, url):
        if self.isResponseSent: # Bail if we already sent a response to requestor
            return True 

        if self.socket is None:
            return False 
        
        try:
            self.socket.send(("HTTP/1.1 307 Temporary Redirect\nLocation: "+str(url)).encode())
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        
        self.socket.close()
        self.isResponseSent = True
        return True
        
    def sendError(self):
        if self.isResponseSent: # Bail if we already sent a response to requestor
            return True 
        
        if self.socket is None:
            return False 
        
        try:
            self.socket.send("HTTP/1.1 404 NOT FOUND".encode())
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass

        self.socket.close()
        self.isResponseSent = True
        return True
    
    def sendHeaders(self, contentType="text/html", httpStatusCode=200, httpStatusMessage="OK", headers=None):
        if self.isResponseSent: # Bail if we already sent a response to requestor
            return None 
        
        if self.socket is None:
            return None 
        
        ret = True
        try:
            response_status = str(httpStatusCode) + " " + str(httpStatusMessage)
            response_status = response_status.replace("(","").replace(")","").replace("'","").replace(",","")
        
            response_headers = [
                    "HTTP/1.1 " + response_status,
                    "Date: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")
                ]
            
            if (headers is None or "Content-Type" not in headers) and contentType is not None:
                response_headers.append("Content-Type: "+contentType)
            
            if headers is None or "Access-Control-Allow-Origin" not in headers:
                response_headers.append("Access-Control-Allow-Origin: *")
            
            if headers is None or "Cache-Control" not in headers:
                response_headers.append("Cache-Control: no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0")

            if headers is None or "Expires" not in headers:
                response_headers.append("Expires: Mon, 1 Jan 2020 00:00:00 GMT")
                
            if headers is None or "Pragma" not in headers:
                response_headers.append("Pragma: no-cache")
            
            if headers is not None:
                for h in headers:
                    response_headers.append(str(h).strip() + ": " + str(headers[h]).strip())
            
                #if "X-ORIGIN" not in headers:
                #    response_headers.append("X-ORIGIN: " + self.origin)
            
            response_text = "\n".join(response_headers)
            
            response_text += "\n\n"
            self.socket.send(response_text.encode())
                
            #self.socket.shutdown(socket.SHUT_RDWR)
            #self.socket.close()
            ret = self.socket
        except:
            self.socket.close()
            ret = None

        return ret
    
    def sendHTTP(self, contentBody=None, contentType="text/html", httpStatusCode=200, httpStatusMessage="OK", headers=None):
        if self.isResponseSent: # Bail if we already sent a response to requestor
            return True 
        
        if self.socket is None:
            return False 
        
        ret = True
        try:
            response_status = str(httpStatusCode) + " " + str(httpStatusMessage)
            response_status = response_status.replace("(","").replace(")","").replace("'","").replace(",","")
            try:
                if contentType.startswith("image/") or contentType.startswith("audio/") or contentType.startswith("video"):
                    response_body = contentBody
                else:
                    response_body = contentBody.encode()
            except (UnicodeDecodeError, AttributeError):
                raise
                response_body = contentBody
        
            response_headers = [
                    "HTTP/1.1 " + response_status,
                    "Date: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")
                ]
            
            if (headers is None or "Content-Type" not in headers) and contentType is not None:
                response_headers.append("Content-Type: "+contentType)
            
            if (headers is None or "Content-Length" not in headers) and contentBody is not None and len(contentBody) > 0:
                response_headers.append("Content-Length: "+str(len(response_body)))
            
            if headers is None or "Access-Control-Allow-Origin" not in headers:
                response_headers.append("Access-Control-Allow-Origin: *")
            
            if headers is None or "Cache-Control" not in headers:
                response_headers.append("Cache-Control: no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0")

            if headers is None or "Expires" not in headers:
                response_headers.append("Expires: Mon, 1 Jan 2020 00:00:00 GMT")
                
            if headers is None or "Pragma" not in headers:
                response_headers.append("Pragma: no-cache")
            
            if headers is not None:
                for h in headers:
                    response_headers.append(str(h).strip() + ": " + str(headers[h]).strip())
            
                #if "X-ORIGIN" not in headers:
                #    response_headers.append("X-ORIGIN: " + self.origin)
            
            response_text = "\n".join(response_headers)
            
            if contentBody is not None and contentBody is not None:
                response_text += "\n\n"
                self.socket.send(response_text.encode())
                self.socket.send(response_body)
            else:
                self.socket.send(response_text.encode())
                
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            self.socket.close()
            ret = False
    
        self.isResponseSent = True
        return ret
    
    def sendJSON(self, contentBody=None, contentType="application/json", httpStatusCode=200, httpStatusMessage="OK", headers=None):
        return self.sendHTTP(contentBody=json.dumps(contentBody), contentType=contentType, httpStatusCode=httpStatusCode, httpStatusMessage=httpStatusMessage, headers=headers)
    
    def validateRequest(self):
        if self.path is None:
            
            if self.command is not None and str(self.command) in ["GET","POST"]:
                self.sendError()
            else:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
                
            return False 
        
        if self.path.lower() == "/favicon.ico":
            self.isFileRequest = True
            self.item = "favicon.svg" # Switched the ICON extension!!!
            self.action = "GET"
            return True
        
        if not isinstance(self.path, str) or str(self.path).lower() in ["/","/admin","/admin/"]:
            self.sendRedirect("/admin/index.html")
            return False
        
        if isinstance(self.path, str):
            parts = self.path.strip("/").split("/") # Trim leading/trailing spaces
            
            if len(parts) > 0:
                tgt = parts[0].lower()

                if tgt == "brain":
                    self.isBrainRequest = True
                elif tgt == "container" or tgt == "device":
                    self.isDeviceRequest = True
                elif tgt == "type":
                    self.isTypeRequest = True
                elif tgt == "admin":
                    self.isFileRequest = True
                else:
                    self.sendError()
                    return False
                
                if self.isBrainRequest:
                    if len(parts) < 2:
                        self.sendError()
                        return False
                    else:
                        self.item = "brain"
                        self.action = parts[1]
                
                elif self.isFileRequest:
                    if len(self.path) < 8:
                        self.sendError()
                        return False
                    else:
                        self.item = self.path[len("/admin/"):]
                        self.action = "GET"
                
                else:
                    if len(parts) < 3:
                        self.sendError()
                        return False
                    else:
                        self.item = parts[1]
                        self.action = parts[2]
                        
                        # Support for JSON requests in format { "command": "ACCEPT_FUNCTION" }
                        if self.action.lower() == "instance" and self.isJSON:
                            if self.JSONData is not None and "command" in self.JSON:
                                self.action = self.JSON["command"]
                        
                if self.isTypeRequest and self.item.lower() == "-":
                    self.item = "all"

            else:
                self.sendError()
                return False
                
        return True
    
    @property
    def JSONData(self):
        if self.JSON is not None:
            return self.JSON
        else:
            if self.headers is None:
                return self.JSON
            
            length = int(self.headers['content-length'])
            try:
                json_body = self.rfile.read(length)
                self.JSON = json.loads(json_body)
            except:
                pass
        
        return self.JSON

