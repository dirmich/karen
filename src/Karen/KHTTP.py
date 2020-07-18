'''
Project Karen: Synthetic Human
Created on Jul 12, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: TCP Server Daemon and HTTP Helpers

'''

import json, logging, time, socket, threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib3, requests, ssl
from cgi import parse_header, parse_multipart
from .KShared import threaded 

def JSON_response(conn, mydata, http_status_code=200, http_status_message="OK"):
    
    response_status = str(http_status_code) + " " + str(http_status_message)
    response_type = "application/json"
    response_body = json.dumps(mydata)
        
    response_text = "HTTP/1.1 "+response_status+"\nDate: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")+"\nContent-Type: "+response_type+"\nAccess-Control-Allow-Origin: *\nContent-Length: "+str(len(response_body)) + "\n\n"
    conn.send(response_text.encode())
    conn.send(response_body.encode())

    conn.shutdown(socket.SHUT_RDWR)
    conn.close()
                    
    return True
    
def JSON_request(url, mydata):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    #url = 'https://localhost:8031/requests'
    #mydata = {'somekey': 'somevalue'}
    
    headers = { "Content-Type": "application/json" }
    mydata = json.dumps(mydata)
    
    x = requests.post(url, data=mydata, headers=headers, verify=False)

    err_val = True
    if x.ok:
        try:
            x_obj = json.loads(x.text)
            if x_obj["error"] == False:
                err_val = False
        except:
            err_val = True

    return { "error": err_val, "message": x.text }

class TCPServer(object):
    def __init__(self, **kwargs):
        
        # Daemon default name (make sure to always set this on inheritance!)
        self._name = "TCP"
        
        # TCP Command Interface
        self.tcp_port = 8080            # TCP Port for listener.
        self.hostname = "localhost"     # TCP Hostname
        self.use_http = True
        self.keyfile=None
        self.certfile=None
        
        self.brain_ip = "localhost"
        self.brain_port = 2020
        self.isOffline = None 
        self.auto_register = False 
        
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.

        self._socket = None             # Socket object (where the listener lives)

        self._TCPServer_thread = None   # Thread object for TCP Server (Should be non-blocking)
        self._TCPServer_running = False # Flag used to indicate if TCP server should be running
        self.lock = threading.Lock()    # Lock for daemon processes
        self._threadPool = []
    
    def _registerWithBrain(self):
            
        if self.use_http == True:
            url = "http://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/register"
        else:
            url = "https://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/register"
            
        mydata = { "command": "REGISTER", "data": { "type": self._name.lower(), "ip": self.hostname, "port": self.tcp_port } }
        
        x_ret = JSON_request(url, mydata)
        
        if x_ret["error"] == False:
            try:
                obj = json.loads(x_ret["message"])
                if ("error" in obj):
                    if (obj["error"] == False):
                        return True
                
                return False
            except:
                return False
        
        return False
    
    @threaded
    def _updateRegistration(self):
        
        i_type = self._name.lower()
        bFirstTime = False
        if self.isOffline is None:
            self.isOffline = True 
            bFirstTime = True 
            
        #bNotRegistered = True
        while self._TCPServer_running:
            try:
                x_stat = self._registerWithBrain()
                if x_stat == True:
                    if self.isOffline == True or bFirstTime:
                        logging.info(i_type + " - Registered with BRAIN successfully.")
                        self.isOffline = False
                        bFirstTime = False
                    else:
                        logging.debug(i_type + " - Registered with BRAIN successfully.")
                    
                if x_stat == False:
                    if self.isOffline == False or bFirstTime:
                        logging.error(i_type + " - Error:  Failed to register with BRAIN.")
                        self.isOffline = True
                        bFirstTime = False
                    else:
                        logging.debug(i_type + " - Error:  Failed to register with BRAIN.") 
    
                    #bNotRegistered = True
                    
                #bNotRegistered = False
            except:
                if self.isOffline == False or bFirstTime:
                    logging.error(i_type + " - Error:  Failed to register with BRAIN.")
                    self.isOffline = True
                    bFirstTime = False
                else:
                    logging.debug(i_type + " - Error:  Failed to register with BRAIN.")
    
                    
                #bNotRegistered = True
            
            time.sleep(10) # Wait 5 secs and try again.
    
    @threaded
    def _acceptConnection(self, conn, address):
        while True:
            # Grab data from the inbound connection (waits for data to be received)
            data = conn.recv(2048)  # Probably larger buffer than will ever be needed for text messages
    
            # If we don't have a valid data object then something went wrong and let's kill the connection.
            if not data:
                break

            text = data.decode().strip()

            if text.lower() == "bye":
                break
            
            if text.lower() == "status":
                response = ("SUCCESS Status online").encode()
                conn.sendall(response)
                break
            
            bKill = False 
            bProcessed = False
            if len(text) > 8 and text[:8].strip().lower() == "command":
                bProcessed = True
                text_command = text[8:].strip()

                res = self._processCommand(text_command) 
            
                if res["error"] == True:
                    response = ("ERROR "+res["message"]).encode()
                    conn.sendall(response)
                else:
                    d = ""
                    if res["data"] is not None:
                        d = "\n" + json.dumps(res["data"])

                    response = ("SUCCESS " + res["message"] + d).encode()
                    conn.sendall(response)
                    
                    if res["kill"] == True:
                        bKill = True
                
            if bProcessed == False:
                response = "ERROR Invalid Command".encode()
                conn.sendall(response)
            
            if bKill:
                self.stop()
            
            break # One loop is all we're allowing for now
            
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        
    def _processCommand(self, text):
        ret = { "error": True, "message": "Invalid Request", "data": None, "kill": False }

        my_cmd = text.lower()
        
        if (my_cmd == "kill"):
            ret["error"] = False
            ret["message"] = "Server is shutting down"
            ret["kill"] = True 
        
        return ret 

    @threaded   
    def _ThreadedTCPServer(self):
        return self._TCPServer()
     
    def _TCPServer(self):
        
        self._TCPServer_running = True 
        
        if (self.auto_register == True):
            self._updateRegistration()
        
        self.lock.acquire()

        self._socket = socket.socket()
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.hostname, self.tcp_port))
        self._socket.listen(self.tcp_clients)
        
        if self.use_http == False:
            logging.debug(self._name + " - SSL Enabled.")
            self._socket = ssl.wrap_socket(self._socket, 
                                       keyfile=self.keyfile, 
                                       certfile=self.certfile,
                                       server_side=True)
        
        self.lock.release()
        
        logging.debug(self._name + " - TCP Server started.")
        
        while self._TCPServer_running:

            try:
                # Accept the new connection
                conn, address = self._socket.accept()
                
                #conn.sendall(str(kconfig.name+" v"+str(kconfig.version)+" [" + self._name + "]\n\n").encode())
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
                
                logging.info(self._name + " - Ctrl+C detected.  Shutting down.")
                self.stop()  # Stop() is all we need to cleanly shutdown.  Will call child class's method first.
                
                return True # Nice and neat closing
                
            except (OSError): # Occurs when we force close the listener on stop()
                
                pass    # this error will be raised on occasion depending on how the TCP socket is stopped
                        # so we put a simple "ignore" here so it doesn't fuss too much.
                        
        return True
    
    def run(self):
        
        return self._TCPServer()

    def stop(self):
        
        self._TCPServer_running = False 
        
        if self._socket is not None:
            
            self.lock.acquire()
            
            # Force the socket server to shutdown
            self._socket.shutdown(0)
            
            # Close the socket
            self._socket.close()
            
            self.lock.release()

            #if self._TCPServer_thread is not None and self._TCPServer_thread.isAlive():
            #    self._TCPServer_thread.join()
            
            # Clear the socket object for re-use
            self._socket = None
        
            
        return True
        
class KHTTPRequest(BaseHTTPRequestHandler):
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