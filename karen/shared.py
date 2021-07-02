"""
Shared library of functions used throughout Karen's various modules
"""

import threading 
import json
import urllib3
import requests
import time 
import socket
import logging 
import sys
import traceback

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from cgi import parse_header, parse_multipart

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

def sendJSONResponse(socketConn, error=False, message=None, data=None, httpStatusCode=200, httpStatusMessage="OK", headers=None):
    """
    Sends a JSON package as an HTTP response to an open socket connection.  Sends all data as "application/json".
    
    Args:
        socketConn (socket):  Open TCP socket from inbound HTTP request.
        error (bool):  Indicator sent on payload to indicate success/failure e.g. { error: False, message: "", data: None }.
        message (str):  The message portion of the payload to be sent e.g. { error: False, message: "", data: None }.
        data (str):  The data portion of the payload to be sent e.g. { error: False, message: "", data: None }.
        httpStatusCode (int):  HTTP status code of response.  Default is 200.
        httpStatusMessage (str):  HTTP status response of response.  Default is "OK".
        headers (list): HTTP Headers to include in result. (optional)
        

    Returns:
        (bool): True on success and False on failure.
    """
    
    payload = {}
    payload["error"] = error
    payload["message"] = message 
    if data is not None:
        payload["data"] = data 
        
    return sendHTTPResponse(socketConn, responseType="application/json", responseBody=json.dumps(payload), httpStatusCode=httpStatusCode, httpStatusMessage=httpStatusMessage, headers=headers)

def sendJSONRequest(url, payLoad, context=None):
    """
    Sends a JSON request to a specified URL using the POST method.
    
    Args:
        url (str):  URL for which to delivery the POST message.
        payLoad (object):  Object to be converted to JSON format and sent as the body of the message.
        context (KContext): Context surrounding the request. (optional)
        
    Returns:
        (bool, str):  Returns a tuple as (bool, str) indicating if the message was successful or failed and any related message.
    """
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    #url = 'https://localhost:8031/requests'
    #mydata = {'somekey': 'somevalue'}
    logger = logging.getLogger("HTTP")
    
    try:
        if context is None:
            context = KContext()
            
        headers = { "Content-Type": "application/json", "X-CLIENT-URL": context.clientURL, "X-BRAIN-URL": context.brainURL }
        request_body = json.dumps(payLoad)
        
        res = requests.post(url, data=request_body, headers=headers, verify=False)
    
        ret_val = False
        if res.ok:
            try:
                res_obj = json.loads(res.text)
                if "error" in res_obj and "message" in res_obj:
                    result = res_obj
                    ret_val = not result["error"]
            except:
                logger.error("Unable to parse response from " + str(url) + "")
                logger.debug(str(res.text))
                pass
        else:
            logger.error("Request failed for " + str(url) + "")
            logger.debug(str(res.text))
    
        return ret_val, res.text

    except requests.exceptions.ConnectionError:
        logger.error("Connection Failed: " + url)
    except:
        logger.error(str(sys.exc_info()[0]))
        logger.error(str(traceback.format_exc()))

    return False, "An error occurred in the HTTP request"

def sendHTTPResponse(socketConn, responseType="text/html", responseBody="", httpStatusCode=200, httpStatusMessage="OK", headers=None):
    """
    Sends a HTTP response to an open socket connection.
    
    Args:
        socketConn (socket):  Open TCP socket from inbound HTTP request.
        responseType (str):  The MIME type of the response message.
        responseBody (str):  The body of the response message.
        httpStatusCode (int):  HTTP status code of response.  Default is 200.
        httpStatusMessage (str):  HTTP status response of response.  Default is "OK".
        headers (list): HTTP Headers to include in result. (optional)

    Returns:
        (bool): True on success and False on failure.
    """
    
    ret = True
    try:
        response_status = str(httpStatusCode) + " " + str(httpStatusMessage)
        response_type = responseType
        response_body = responseBody
    
        response_headers = [
                "HTTP/1.1 " + response_status,
                "Date: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z"),
                "Access-Control-Allow-Origin: *"
            ]
        
        
        if headers is None or "Content-Type" in headers:
            response_headers.append("Content-Type: "+response_type)
        
        if headers is None or "Content-Length" in headers:
            response_headers.append("Content-Length: "+str(len(response_body)))
        
        response_text = "\n".join(response_headers) + "\n\n"
        socketConn.send(response_text.encode() + response_body.encode())
    
        socketConn.shutdown(socket.SHUT_RDWR)
        socketConn.close()
    except:
        ret = False
                    
    return ret

class KHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Class to parse an HTTP request into its parts for GET and POST variables, paths, etc. and can handle multipart/form-data requests.
    """
    
    def __init__(self, request_text):
        """
        Request Handler Initialization
        
        Args:
            request_text (str):  The full RFC-compliant HTTP request.
        """
        
        self.rfile = request_text
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.json_body = None
        
    def send_error(self, code, message):
        """
        Sets the error code and message for errors.
        
        Args:
            code (int):  Error code for message.
            message (str):  Message text for error
        """
        
        self.error_code = code
        self.error_message = message
    
    def parse_GET(self):
        """
        Parses the variables from the query string of the HTTP message.
        
        Returns:
            (dict): name/value pairs representing the query string values
        """
        
        getvars = parse_qs(urlparse(self.path).query)
        
        return getvars
        
    def parse_POST(self):
        """
        Parses the variables from the body of the HTTP message.
        
        Returns:
            (dict): name/value pairs representing the POST values
        """
        
        postvars = {}
        
        if "content-type" in self.headers:
            ctype, pdict = parse_header(self.headers['content-type'])
            if ctype == 'multipart/form-data':
                postvars = parse_multipart(self.rfile, pdict)
            elif ctype == "application/json":
                length = int(self.headers['content-length'])
                try:
                    if self.json_body is None:
                        self.json_body = self.rfile.read(length)
                    return json.loads(self.json_body)
                except Exception as e:
                    return { "error": True, "message": "Error occured: "+str(e) }
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers['content-length'])
                postvars = parse_qs(
                    self.rfile.read(length).decode(),  # Added ".decode()" which forces everything to simple strings
                    keep_blank_values=1)
                
        
        return postvars
    
class KJSONRequest:
    """
    Helper class for storing the portions of an inbound JSON request.
    """
    
    def __init__(self, inContainer, inSocket, inPath, inPayload, context=None):
        """
        JSON Request Initialization
        
        Args:
            inContainer (object):  The containing object on which the request was received such as the Brain or DeviceContainer.
            inSocket (socket): The client socket on which to send any appropriate responses.
            inPath (str): The relative path of the request (e.g. "control").
            inPayload (object): The JSON-parsed payload to store for referencing
            context (KContext): Context surrounding the request. (optional)
        """
        
        self.container = inContainer
        self.conn = inSocket
        self.path = inPath
        self.payload = inPayload
        self.context = context
        
    def sendResponse(self, error=False, message="", data=None, httpStatusCode=200, httpStatusMessage="OK", headers=None):
        """
        Sends an HTTP response to the requesting client to close the connection.
        
        Args:
            error (bool):  Indicator sent on payload to indicate success/failure e.g. { error: False, message: "", data: None }.
            message (str):  The message portion of the payload to be sent e.g. { error: False, message: "", data: None }.
            data (str):  The data portion of the payload to be sent e.g. { error: False, message: "", data: None }.
            httpStatusCode (int):  HTTP status code of response.  Default is 200.
            httpStatusMessage (str):  HTTP status response of response.  Default is "OK".
            headers (list): HTTP Headers to include in result. (optional)
            
        Returns:
            (bool):  True on success and False on failure.
        """
        
        ret = sendJSONResponse(socketConn=self.conn, error=error, message=message, data=data, httpStatusCode=httpStatusCode, httpStatusMessage=httpStatusMessage, headers=headers)
        return ret
    
class KContext():
    def __init__(self, clientURL=None, brainURL=None):
        """
        Context of the inbound request.
        
        Args:
            clientURL (str):  Client address from which the request was made or None if coming through control panel.            
            brainURL (str):  Brain address from which the request was processed or None.
        """

        self.clientURL = clientURL
        self.brainURL = brainURL
        
    def get(self):
        """
        Gets the context as a dict
        """
        
        return { "clientURL": self.clientURL, "brainURL": self.brainURL }
    
    def load(self, data):
        """
        Sets the context from a dict (same format pulled from .get()).
        
        Args:
            data (dict):  The data for the context
        
        Returns:
            (bool):  True on success or False on failure.
        """
        
        if not isinstance(data, dict):
            return False 
        
        self.clientURL = data["clientURL"] if "clientURL" in data else None
        self.brainURL = data["brainURL"] if "brainURL" in data else None
        
        return True