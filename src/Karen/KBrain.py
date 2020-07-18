'''
Project Karen: Synthetic Human
Created on Jul 12, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: Brain Daemon

'''

import os, sys
sys.path.insert(0,os.path.join(os.path.abspath(os.path.dirname(__file__)), "skills"))

import logging, json, socket, time
from .KHTTP import TCPServer, KHTTPRequest, JSON_request, JSON_response
from . import KVersion 
from .KSkillManager import SkillManager
from .KShared import threaded, People, Person 

class Brain(TCPServer):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._name = "BRAIN"
        
        self.hostname = kwargs["ip"]
        self.tcp_port = kwargs["port"]

        self.webgui_path = kwargs["web_folder"]
        self.use_http = kwargs["use_http"]
        
        self.url_prefix = "https://"
        if self.use_http:
            self.url_prefix = "http://"
        
        self.ssl_keyfile = kwargs["ssl_keyfile"]
        self.ssl_certfile = kwargs["ssl_certfile"]

        self.mem_path = kwargs["mem_path"]
        if self.mem_path is None:
            import tempfile
            self.mem_path = tempfile.gettempdir()
        
        os.makedirs(self.mem_path, exist_ok=True)
        
        self.skill_manager = None   # Used to store the skillmanager object
    
    @threaded
    def _acceptConnection(self, conn, address):
        
        try:
            try:
                r = KHTTPRequest(conn.makefile(mode='b'))
                    
                path = str(r.path).lower()
                if ("?" in path):
                    path = path[:path.index("?")]
                    
                payload = {}
                if r.command.lower() == "post":
                    payload = r.parse_POST()
                else:
                    payload = r.parse_GET()
                
                if path == "/favicon.ico" or path == "/webgui/favicon.ico":
                    response_status = "200 OK"
                    response_type = "image/svg+xml"
                    
                    myfile = os.path.join(self.webgui_path, "favicon.svg")
                    with open(myfile, mode='r') as f:
                        response_body = f.read()
                             
                elif (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
                    
                    # Kill, Start, Stop

                    if "command" in payload:
                        if str(payload["command"]).lower() == "say":
                            if "data" in payload:
                                res = self.say(str(payload["data"]))
                                if res["error"] == False:
                                    JSON_response(conn, res)
                                    return True
                                else:
                                    JSON_response(conn, res)
                                    return False

                            else:
                                JSON_response(conn, { "error": True, "message": "Invalid string value in data." })
                                return False
                        elif str(payload["command"]).lower() == "start_listener":
                            x_ret = self.sendCommandToDevice("listener",{ "command": "START_LISTENER" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "stop_listener":
                            x_ret = self.sendCommandToDevice("listener",{ "command": "STOP_LISTENER" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "start_watcher":
                            x_ret = self.sendCommandToDevice("watcher",{ "command": "START_WATCHER" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "stop_watcher":
                            x_ret = self.sendCommandToDevice("watcher",{ "command": "STOP_WATCHER" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "train":
                            x_ret = self.sendCommandToDevice("watcher",{ "command": "TRAIN" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "start_visualizer":
                            x_ret = self.sendCommandToDevice("speaker",{ "command": "START_VISUALIZER" })
                            JSON_response(conn, x_ret)
                            return True
                        elif str(payload["command"]).lower() == "stop_visualizer":
                            x_ret = self.sendCommandToDevice("speaker",{ "command": "STOP_VISUALIZER" })
                            JSON_response(conn, x_ret)
                            return True
                        else:
                            JSON_response(conn, { "error": True, "message": "Invalid command." }, http_status_code=500, http_status_message="Internal Server Error")
                            return False
                            
                    
                    JSON_response(conn, { "error": True, "message": "Invalid command." }, http_status_code=500, http_status_message="Internal Server Error")
                    return False
    
                elif (len(path) == 5 and path == "/data") or (len(path) > 5 and path[:6] == "/data/"):
                    
                    if "type" in payload:
                        if payload["type"].lower() == "audio_input":
                            try:
                                logging.debug(self._name + " - Parsing speech: " + str(payload["data"]))

                                utterences = self.getSpeakerData()
                                utterences.append({ "phrase": str(payload["data"]), "time": time.time() })
                                if len(utterences) > 10:
                                    utterences.pop(0)
                                self.saveSpeakerData(utterences)

                                result = self.skill_manager.parseInput(payload["data"])
                                if result["error"] == True:
                                    if "thanks" in payload["data"] or "thank you" in payload["data"]:
                                        res = self.say("You're welcome.")
                                        if res["error"] == False:
                                            JSON_response(conn, res)
                                        else:
                                            JSON_response(conn, res)
                                    else:
                                        logging.error(self._name + " - Error in speech parsing: " + str(result["message"]))
                                        JSON_response(conn, { "error": True, "message": "Error in speech parsing: " + str(result["message"]) })
                                else:
                                    JSON_response(conn, { "error": False, "message": "AUDIO_INPUT received." })

                                return True
                            except:
                                JSON_response(conn, { "error": True, "message": "Invalid AUDIO_INPUT data request." })
                                return False
                            
                        if payload["type"].lower() == "watcher_data":
                            try:
                                
                                try:
                                    in_data = payload["data"]
                                    w_data = self.getWatcherData()
                                    people = People(w_data)
                                    people.removePerson(-1)
                                    
                                    for z in in_data:
                                        p = Person(idx=z["id"], confidence=z["distance"], width=z["dimensions"]["width"], height=z["dimensions"]["height"], x=z["coordinates"]["x"], y=z["coordinates"]["y"])
                                        
                                        if p.idx == -1:
                                            people.addPerson(p, True)
                                        else:
                                            people.addPerson(p)
                                    #print(people.info())
                                    self.saveWatcherData(people.info())
                                except Exception as e:
                                    print(e)
                                    raise
                                
                                JSON_response(conn, { "error": False, "message": "WATCHER_DATA received." })
                                return True
                            except:
                                JSON_response(conn, { "error": True, "message": "Invalid WATCHER_DATA request." })
                                return False

                    JSON_response(conn, { "error": True, "message": "Invalid data object." }, http_status_code=500, http_status_message="Internal Server Error")
                    return False
    
                elif (len(path) == 9 and path == "/register") or (len(path) > 9 and path[:10] == "/register/"):

                    try:
                        if "ip" in payload["data"] and str(payload["data"]["ip"]) != "":
                            incoming_ip = str(payload["data"]["ip"])
                        else:
                            incoming_ip = str(address[0]) 
                        
                        if (str(payload["command"]).lower() == "register"):
                            devices = self.getDevices()
                                
                            bFound = False
                            bStatus = False
                            for d in devices:
                                if str(d["ip"]).lower() == incoming_ip.lower() and int(d["port"]) == int(payload["data"]["port"]) and (str(d["type"]).lower() == str(payload["data"]["type"]).lower()):
                                    bFound = True
                                    bStatus = bool(d["status"])
                                    d["status"] = True
                                    break

                            if bFound == False:
                                
                                jobj = { "type": str(payload["data"]["type"]).lower(), "ip": incoming_ip.lower(), "port": int(payload["data"]["port"]), "status": True }
                                devices.append(jobj)

                            self.saveDevices(devices)
                            
                            if bFound == False or bFound == True and bStatus == False:
                                logging.info(self._name + " - " + str(payload["data"]["type"]).upper() + " device at " + str(incoming_ip) + ":" + str(payload["data"]["port"]) + " registered and is Online")
                            else:
                                logging.debug(self._name + " - " + str(payload["data"]["type"]).upper() + " device at " + str(incoming_ip) + ":" + str(payload["data"]["port"]) + " registered and is Online")

                            JSON_response(conn, { "error": False, "message": "Register command succeeded." })
                            return True
                        else:
                            JSON_response(conn, { "error": True, "message": "Invalid command." })
                            return False
                        
                    except Exception as e:
                        JSON_response(conn, { "error": True, "message": "Register failed: "+str(e) })
                        return False
    
                elif (len(path) == 7 and path == "/status") or (len(path) > 7 and path[:8] == "/status/"):
                    
                    
                    if path == "/status/devices":
                        if "command" in payload and str(payload["command"]).lower() == "get-all-current":
                            JSON_response(conn, { "error": False, "message": "Device list completed.", "data": self.getDevices() })
                            return True
                        else:
                            JSON_response(conn, { "error": True, "message": "Invalid command." }, http_status_code=500, http_status_message="Internal Server Error")
                            return False
                    else:
                        JSON_response(conn, { "error": False, "message": "Device is online." })
                        return True
                    
                elif (len(path) == 7 and path == "/webgui") or (len(path) > 7 and path[:8] == "/webgui/"):
                    
                    path = path.replace("/../","/").replace("/./","/") # Ugly parsing.  Probably should regex this for validation.
                    
                    if path == "/webgui" or path == "/webgui/":
                        path = "/webgui/index.html"
                    
                    myfile = os.path.join(self.webgui_path, path[8:])
                    if os.path.exists(myfile):
                        response_status = "200 OK"
                        response_type = "text/html"
                        with open(myfile, mode='r') as f:
                            response_body = f.read()
                        
                        response_body = response_body.replace("__APP_NAME__", KVersion.__APP_NAME__).replace("__APP_VERSION__", "v"+KVersion.rev)
                    else:
                        response_status = "404 Not Found"
                        response_type = "text/html"
                        response_body = "<html><body>File not found</body></html>"
    
                else:
                    response_status = "404 Not Found"
                    response_type = "application/json"
                    response_body = json.dumps({ "error": True, "message": "Invalid request" })
            except Exception as e:
                JSON_response(conn, { "error": True, "message": "Request failed: "+str(e) }, http_status_code=500, http_status_message="Internal Server Error")
                return False
                
            response_text = "HTTP/1.1 "+response_status+"\nDate: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")+"\nContent-Type: "+response_type+"\nContent-Length: "+str(len(response_body)) + "\n\n"
            conn.send(response_text.encode())
            conn.send(response_body.encode())

            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            return True
        
        except Exception as e:
            logging.debug(self._name + " - Error in HTTP Receipt: " + str(e))
        
        return False        
    
    def getDevices(self):
        return self.getFileData("devices.json")
    
    def getFileData(self, file_name):
        t_file = os.path.join(self.mem_path, self._name + "." + file_name)
        t = []
        if os.path.exists(t_file):
            with open(t_file, 'r') as fp:
                t = json.load(fp)
                
        return t
    
    def getSpeakerData(self):
        return self.getFileData("speaker_data.json")
    
    def getWatcherData(self):
        return self.getFileData("watcher_data.json")
    
    def saveDevices(self, devices):
        return self.saveFileData(devices, "devices.json")
    
    def saveFileData(self, file_data, file_name):
        try:
            t_file = os.path.join(self.mem_path, self._name + "." + file_name)
            if os.path.exists(self.mem_path):
                with open(t_file, 'w') as fp:
                    json.dump(file_data, fp, indent=4)
            else:
                return False
        except:
            return False
            
        return True

    def saveSpeakerData(self, speaker_data):
        return self.saveFileData(speaker_data, "speaker_data.json")
    
    def saveWatcherData(self, watcher_data):
        return self.saveFileData(watcher_data, "watcher_data.json")
        

    def say(self, text):

        logging.info(self._name + " - Saying: "+text)

        # Synchronous Requests to Start Speech Output
        x_ret = { "error": True, "message": "Command not completed." }

        try:

            url_prefix = "https://"
            if self.use_http:
                url_prefix = "http://"

            devices = self.getDevices()

            dSave = False

            for d in devices:
                if d["type"] == "listener" and d["status"] == True:
                    listener_url = url_prefix + d["ip"] + ":" + str(d["port"]) + "/control"
                    try:
                        JSON_request(listener_url, { "command": "AUDIO_OUT_START" })
                    except:
                        d["status"] = False
                        dSave = True
                        pass 
                    
            # Send to Primary Speaker
            speaker_dev = None
            for d in devices:
                if d["type"] == "speaker" and d["status"] == True:
                    speaker_dev = url_prefix + d["ip"] + ":" + str(d["port"]) + "/control"
                    try:
                        x_ret = JSON_request(speaker_dev, { "command": "SAY", "data": text })
                    except Exception as e:
                        x_ret = { "error": True, "message": str(e) }
                        d["status"] = False
                        dSave = True
                        
        
            for d in devices:
                if d["type"] == "listener" and d["status"] == True:
                    listener_url = url_prefix + d["ip"] + ":" + str(d["port"]) + "/control"
                    try:
                        JSON_request(listener_url, { "command": "AUDIO_OUT_END" })
                    except:
                        d["status"] = False
                        dSave = True
                        pass 
                    
            if dSave == True:
                self.saveDevices(devices)
            
        except Exception as e:
            logging.debug(self._name + " - SAY task error: " + str(e))
            return { "error": True, "message": str(e) }
        
        if (x_ret["error"] == False):
            return { "error": False, "message": "Say completed successfully." }
        else:
            return { "error": True, "message": x_ret["message"] }

    def sendCommandToDevice(self, x_type,x_command):
        logging.info(self._name + " - Sending command to "+x_type)

        try:

            url_prefix = "https://"
            if self.use_http:
                url_prefix = "http://"

            devices = self.getDevices()

            dSave = False
            bAnySuccess = False
            bAllSuccess = True

            for d in devices:
                if d["type"].lower() == x_type.lower() and d["status"] == True:
                    device_url = url_prefix + d["ip"] + ":" + str(d["port"]) + "/control"
                    try:
                        ret_val = JSON_request(device_url, x_command)
                        if ret_val["error"] == False:
                            bAnySuccess = True
                        else:
                            bAllSuccess = False
                            
                    except:
                        d["status"] = False
                        dSave = True
                        pass 
                    
            if dSave == True:
                self.saveDevices(devices)
            
        except Exception as e:
            logging.debug(self._name + " - SAY task error: " + str(e))
            return { "error": True, "message": str(e) }
        
        if (bAnySuccess == True) and (bAllSuccess == True):
            return { "error": False, "message": "Command completed successfully." }
        
        return { "error": True, "message": "One or more commands failed" }
        
    def stop(self):
        self.skill_manager.stop()
        return super().stop()
    
    def run(self):
        
        self.skill_manager = SkillManager(self)
        self.skill_manager.initialize()
        
        #url_prefix = "https://"
        #if self.use_http:
        #    url_prefix = "http://"
                
        #devices = self.getDevices()
        #for d in devices:

        #    device_url = url_prefix + d["ip"] + ":" + str(d["port"]) + "/status"
        #    try:
        #        x_stat, x_text = sendHTTPRequest(device_url, { "command": "STATUS" })
        #    except:
        #        x_stat = False
            
            
        #    if (x_stat):
        #        logging.info(self._name + " - Cached " + str(d["type"]).upper() + " device at " + str(d["ip"]) + ":" + str(d["port"]) + " is Online")
        #    else:
        #        logging.info(self._name + " - Cached " + str(d["type"]).upper() + " device at " + str(d["ip"]) + ":" + str(d["port"]) + " is Offline")

        #    d["status"] = x_stat # If the connection was successful the status is online. 
            
        #self.saveDevices(devices)
        
        super().run()