'''
Project Karen: Synthetic Human
Created on Jul 12, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: Speaker Daemon

'''
import os, logging, json
from .KHTTP import TCPServer, KHTTPRequest, JSON_response
from .KShared import threaded

import subprocess, signal

class Speaker(TCPServer):
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)

        # Daemon default name (make sure to always set this on inheritance!)
        self._name = "SPEAKER"
        
        # TCP Command Interface
        self.tcp_port = kwargs["port"]            # TCP Port for listener.
        self.hostname = kwargs["ip"]     # TCP Hostname
        self.use_http = kwargs["use_http"]
        self.keyfile=kwargs["ssl_keyfile"]
        self.certfile=kwargs["ssl_certfile"]
        
        self.brain_ip=kwargs["brain_ip"]
        self.brain_port=kwargs["brain_port"]
        self.auto_register = True
        
                            
        import tempfile
        self.temp_folder = tempfile.gettempdir()

        # Visualizer process ID (used to kill it on stop() calls)
        self._visualizer = None
        self.visualizerCommand = kwargs["visualizer"]   # This is ideally an array of shell commands/vars
                                                                # e.g. ["xterm","-fullscreen","-e","vis"]
                                                                # or   "vis"

        # Just in case we set a visualizer value, let's give it a shot.
        if self.visualizerCommand is not None:
            
            # Clean it up (no extra line breaks or spaces)
            self.visualizerCommand = str(self.visualizerCommand).strip()
            
            # Now lets see if it is an array or just plain text.  (Arrays work better with "subprocess" in python.
            if (len(self.visualizerCommand) > 0) and ("[" == self.visualizerCommand.strip()[:1] or ("{" == self.visualizerCommand.strip()[:1])):
                try:
                    # An array!  Yay!
                    self.visualizerCommand = json.loads(self.visualizerCommand)
                except:
                    # Default to whatever we got... we'll give it a shot
                    self.visualizerCommand = str(kwargs["speaker_visualizer"]).strip()
        

    @threaded
    def _acceptConnection(self, conn, address):
        r = KHTTPRequest(conn.makefile(mode='b'))
        
        path = str(r.path).lower()
        if ("?" in path):
            path = path[:path.index("?")]
        
        payload = {}
        if r.command.lower() == "post":
            payload = r.parse_POST()
        else:
            payload = r.parse_GET()
            
        if (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
            
            if "command" in payload:
                my_cmd = str(payload["command"]).lower()
                
                if my_cmd == "kill":
                    
                    JSON_response(conn, { "error": False, "message": "Server is shutting down." })
        
                    self.stop()
                    return True
            
                elif my_cmd == "say":
                    
                    if "data" in payload and payload["data"] is not None:
                        say_file = os.path.join(self.temp_folder, "say.out")
            
                        with open(say_file, 'w') as f:
                            f.write(str(payload["data"])) 
            
                        os.system("festival --tts "+say_file )
                        os.remove(say_file)
                    
                        JSON_response(conn, { "error": False, "message": "Speak command complete." })
                        return True 
                    else:
                        JSON_response(conn, { "error": True, "message": "Speak command missing text." })
                        return False
                elif my_cmd == "start_visualizer":
                    if self._startVisualizer():
                        JSON_response(conn, { "error": False, "message": "Visualizer started successfully." })
                        return True 
                    else:
                        JSON_response(conn, { "error": True, "message": "Visualizer failed to start.  It may already be running." })
                        return False 
                    
                elif my_cmd == "stop_visualizer":
                    if self._stopVisualizer():
                        JSON_response(conn, { "error": False, "message": "Visualizer stopped successfully." })
                        return True 
                    else:
                        JSON_response(conn, { "error": True, "message": "Visualizer failed to stop.  It may already be stopped." })
                        return False 
                        
                else:
                    JSON_response(conn, { "error": True, "message": "Invalid command." }, http_status_code=500, http_status_message="Internal Server Error")
                    return False

        
        JSON_response(conn, { "error": True, "message": "Invalid request" }, http_status_code=404, http_status_message="Not Found")
        return False

    def _startVisualizer(self):
        """We all like pretty things.  Why not put a reactive audio visualizer to make it feels like HAL.
        
        And if you don't know who HAL is then you have some research to do.
        
        Note that this is only for a reactive display of the audio while it is being spoken.  It's just
        a visual effect.  It has no real value to the overall code."""
        
        # Check if we already have a visualizer running.
        if (self._visualizer is not None):
            logging.debug(self._name + " - Visualizer already started")
            return False

        # Check if we have a command to try to execute.
        if self.visualizerCommand is not None:
            
            # Here goes nothing.
            try:
                self._visualizer = subprocess.Popen(self.visualizerCommand, preexec_fn=os.setsid, stderr=subprocess.PIPE)
                logging.info(self._name + " - Visual started")
            except:
                logging.info(self._name + " - Visual failed to start")
                return False

        # This isn't a critical function so we'll pretend like everything is great.
        return True
    
    def _stopVisualizer(self):
        """Stop the visualizer.  (Who needed that anyway.)
        
        Note that this is only for a reactive display of the audio while it is being spoken.  It's just
        a visual effect.  It has no real value to the overall code."""
        
        # Do we have something to kill?
        if (self._visualizer is not None):
            # Okay, let's try not to break too many things in our operating system.        
            os.killpg(os.getpgid(self._visualizer.pid), signal.SIGTERM)  # Just kill our subprocess's page
            self._visualizer.terminate() # Now kill the subprocess itself
            self._visualizer.wait() # Now wait for all that to finish processing
            self._visualizer = None # And reset so we can do it all over again.
            logging.info(self._name + " - Visualizer stopped")
        else:
            logging.debug(self._name + " - Visualizer not running")
            return False
        
        # Yep, another one of those really important return values that is totally dependent on what we just did.
        return True

    def run(self):
        if self.visualizerCommand is not None:
            self._startVisualizer()
            
        return super().run()

    def stop(self):
        if self._visualizer is not None:
            self._stopVisualizer()
            
        return super().stop()