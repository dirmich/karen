'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Karen's library of shared functions and classes
'''

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
    """Returns the part of the day based on the system time
    based on generally acceptable breakpoints."""
    
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
    """Thread wrapper shortcut using @threaded prefix"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper

def sendJSONResponse(socketConn, error=False, message=None, data=None, httpStatusCode=200, httpStatusMessage="OK"):
    payload = {}
    payload["error"] = error
    payload["message"] = message 
    if data is not None:
        payload["data"] = data 
        
    return sendHTTPResponse(socketConn, responseType="application/json", responseBody=json.dumps(payload), httpStatusCode=httpStatusCode, httpStatusMessage=httpStatusMessage)

def sendJSONRequest(url, payLoad):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    #url = 'https://localhost:8031/requests'
    #mydata = {'somekey': 'somevalue'}
    logger = logging.getLogger("HTTP")
    
    try:
        headers = { "Content-Type": "application/json" }
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

def sendHTTPResponse(socketConn, responseType="text/html", responseBody="", httpStatusCode=200, httpStatusMessage="OK"):
    
    ret = True
    try:
        response_status = str(httpStatusCode) + " " + str(httpStatusMessage)
        response_type = responseType
        response_body = responseBody
    
            
        response_text = "HTTP/1.1 "+response_status+"\nDate: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")+"\nContent-Type: "+response_type+"\nAccess-Control-Allow-Origin: *\nContent-Length: "+str(len(response_body)) + "\n\n"
        socketConn.send(response_text.encode())
        socketConn.send(response_body.encode())
    
        socketConn.shutdown(socket.SHUT_RDWR)
        socketConn.close()
    except:
        ret = False
                    
    return ret

class KHTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = request_text
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.json_body = None
        
    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message
    
    def parse_GET(self):
        
        getvars = parse_qs(urlparse(self.path).query)
        
        return getvars
        
    def parse_POST(self):
        
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
    def __init__(self, inContainer, inSocket, inPath, inPayload):
        self.container = inContainer
        self.conn = inSocket
        self.path = inPath
        self.payload = inPayload
        
    def sendResponse(self, error=False, message="", data=None, httpStatusCode=200, httpStatusMessage="OK"):
        ret = sendJSONResponse(socketConn=self.conn, error=error, message=message, data=data, httpStatusCode=httpStatusCode, httpStatusMessage=httpStatusMessage)
        return ret