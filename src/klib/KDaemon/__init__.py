"""Karen Project : Daemon functions

This provides a generic way to create new functions
that can be interacted with through a standard TCPServer
command/response process.  (Inheriting the Daemon class
effectively achieves this.)"""

import os, sys, time, logging, threading, socket
from ctypes import *
import pyaudio, queue, webrtcvad, collections
import numpy as np
import deepspeech

import json
import subprocess
import signal as sig

import cv2

from PIL import Image

import kconfig
import klib.KShared as ks

def threaded(fn):
    """Thread wrapper shortcut using @threaded prefix"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper

def py_error_handler(filename, line, function, err, fmt):
    """Used as the handler for the trapped C module errors"""

    # Convert the parameters to strings for logging calls
    fmt = fmt.decode("utf-8")
    filename = filename.decode("utf-8")
    function = function.decode('utf-8')

    # Poor attempt at formating the output of the trapped errors
    fmt = "CTYPES - " + fmt
        
    if ("%s" in fmt) and ("%i" in fmt):
        logging.debug(fmt % (function, line))
    elif ("%s" in fmt):
        logging.debug(fmt % (function))
    else:
        logging.debug(fmt)
    return

class SilenceStream():
    """Hides C library messages by redirecting to log file"""
    
    def __init__(self, stream, log_file=None, file_mode='a'):
        """Redirect stream to log file"""
        
        self.fd_to_silence = stream.fileno() # Store the stream we're referening
        self.log_file = log_file # Store the log file to redirect to
        self.file_mode = file_mode # Append vs. Writex

    def __enter__(self):
        """Perform redirection"""

        if (self.log_file is None): 
            return # No log file means we can skip this and let output flow as normal.
        
        self.stored_dup = os.dup(self.fd_to_silence) # Store the original pointer for the stream
        self.devnull = open(self.log_file, self.file_mode) # Get a pointer for the new target
        os.dup2(self.devnull.fileno(), self.fd_to_silence) # Redirect to the new pointer

    def __exit__(self, exc_type, exc_value, tb):
        """Restore to original state before redirection"""

        if (self.log_file is None): 
            return  # No log file means we can skip this as nothing needs to change.
        
        os.dup2(self.stored_dup, self.fd_to_silence) # Restore the pointer to the original
        self.devnull = None # Cleanup
        self.stored_dup = None # Cleanup
        
class Daemon(object):
    """Simple TCP Server Daemon"""
    
    def __init__(self, **kwargs):
        
        # Daemon default name (make sure to always set this on inheritance!)
        self._name = "TCP"
        
        # TCP Command Interface
        self.tcp_port = None            # TCP Port for listener.
        self.hostname = "localhost"     # TCP Hostname
            
        self.tcp_clients = 5            # Simultaneous clients.  Max is 5.  This is probably overkill.

        self._socket = None             # Socket object (where the listener lives)
        self._kwargs = kwargs           # We save all args just in case.
        self._SOCKET_ALIVE = False      # Used like a KILL_SWITCH with False meaning to kill the listener.
        
    @threaded
    def _processInbound(self, connection, address):
        """Handle the inbound TCP request and parse format and hand off for validation"""
        
        conn = connection # Lazy coding because I copy examples in Py Docs
        
        while True:
            # Grab data from the inbound connection (waits for data to be received)
            data = conn.recv(2048).decode()  # Probably larger buffer than will ever be needed for text messages
            
            # If we don't have a valid data object then something went wrong and let's kill the connection.
            if not data:
                break

            # Get the full text.
            # It may come in in a variety of ways and may or may not contain headers.
            #
            # Standard Text command looks like this:
            #     COMMAND [DATA HERE]
            #
            # Alternatively a JSON object can be provided, but to set JSON a header must
            # be included of "Context-Type: JSON"
            #
            # Standard JSON commands look like this (at a minimum, but may contain other objects):
            #     { "command": "[DATA_HERE]" }
            
            text = str(data).strip()
            
            # Only care if we actually have content to parse.  Otherwise keep waiting for data.
            if (text != ""):

                # For parsing content types
                contentType = None
                
                # Check if we have headers
                if (text.find("\n\n") > 0):
                    
                    # Break out text into headers and content
                    headers = text[:text.find("\n\n")].strip().split("\n")
                    content = text[text.find("\n\n"):].strip()

                    # Parse headers.
                    for h in headers:
                        if (":" in h):  # Valid headers will normally have a colon in them.
                            name_val = h.split(":")
                            
                            # Check content types (It is possible that we get multiple content-type headers with one of each.
                            # If we get multiple we'll assume the FIRST one that we encountered.
                            
                            if contentType is None and name_val[0].strip().lower() == "content-type" and name_val[1].strip().lower() == "json":
                                contentType = "json"
                
                else:
                    content = text.strip()

                # If we didn't get a Content-Type header then we'll assume it was text
                if contentType is None:
                    contentType = "text"
                  
                # ========================================  
                # Based on the content type, let's do some processing!
                
                if contentType == "json":
                    # WooHoo, complex data empowered by JSON

                    if (content == ""):
                        # If we didn't get a valid command then let's kill it now.
                        conn.sendall(json.dumps({ "error": True, "message": "INVALID COMMAND" }).encode())

                    else:

                        # Okay, let's see if we can process what we received.                            
                        resp = self.processCommand(content, "json") # Probably should consider changing expected variable to object rather than string
                        
                        # let's check if it is one of our special use cases
                        try:
                            # Note:  I don't much like doing this as it means I have to carry this object, but such is life for now.
                            c = json.loads(content) 
                            if str(c["command"]).strip().lower() == "kill" or str(c["command"]).strip().lower() == "kill_all":
                                conn.sendall(json.dumps({ "error": False, "message": "OK" }).encode())
                                break
                            else:
                                # If not one of our special use cases then return what we got as a response from our attempt at processing.
                                conn.sendall(resp.encode())  
                        except:
                            # If we couldn't parse the inbound then we should still send the response we processed.
                            conn.sendall(resp.encode()) 
                            
                else:
                    # Defaults to TEXT content type

                    # This is really useless.  If a person is telnetting for validation it's a way to kill the connection.
                    # Waste of code in my opinion.
                    if content == "bye":
                        break

                    # Let's split into our pieces ("COMMAND TEXT HERE" gets broken into ["COMMAND", "TEXT HERE"]
                    s = content.split(" ",1)

                    # If we have a "real" command (one in the right format) then try to process it.
                    if len(s) > 1 and s[0].lower().strip() == "command":
                        
                        # Overrideable function here.  Otherwise the only real command is "kill"
                        resp = self.processCommand(s[1].strip(), "text")
                        
                        conn.sendall(str(resp+"\n").encode()) # Send the response to the requestor (usually "OK" or "ERROR Message Here" type result.

                        # If this is one of our special use cases then we kill the connection.                    
                        if (s[1].strip().lower() == "kill") or (s[1].strip().lower() == "kill_all"):
                            break

                    else:
                        # If not a valid command then just we let the requestor know
                        conn.sendall("INVALID COMMAND".encode())
                    
        # If we're finished receiving data then we close the connection.
        conn.close()
    
    def processCommand(self, s_in, s_type="text"):
        """Process incoming Commands/Data
        
        Overridable in child classes to add additional functions.
        Just be sure to call super().processCommand(s_in, s_type) as a final action"""

        # Check type
        if s_type.lower().strip() == "json":
            try:
                # Attempt to parse incoming string into JSON object
                data = json.loads(s_in)
                
                # In base Daemon the only command we care about is if we need to stop running.
                if str(data["command"]).lower().strip() == "kill":
                    
                    logging.info(self._name + " - KILL command received. Stopping all services.")
                    
                    # Note: This calls the child stop() function first if overriden
                    self.stop() 
                    
                    # Return a generic "OK" response.
                    return json.dumps({ "error": False, "message": "OK" })
                
            except:
                # Error.  Assuming this is because of the json.loads() line above.
                return json.dumps({ "error": True, "message": "Error parsing JSON request" })
            
            # If we made it this far then something went wrong.
            return json.dumps({ "error": True, "message": "INVALID COMMAND" })
        
        else:
            # Default to TEXT command
            
            # In base Daemon the only command we care about is if we need to stop running.
            if s_in.lower() == "kill":
                            
                logging.info(self._name + " - KILL command received. Stopping all services.")
                
                # Note: This calls the child stop() function first if overriden
                self.stop()
                
                # Return a generic "OK" response.
                return "OK" # Technically the socket may be shutdown so this could die in transit

        # We should not have made it this far so return a generic error.
        return "INVALID COMMAND"
        
    def run(self):
        """The main thread runtime for the Daemon.
        
        Will continue running until socket is shut down or fails."""
        
        # Make sure we have a valid TCP port to listen on
        if self.tcp_port is None:
            raise RuntimeError("Invalid tcp port specified")

        # (Re)set the SOCK_ALIVE value so that any prior stop commands are no longer applicable
        self._SOCKET_ALIVE = True
        
        # If socket is already initialized then we need to fail (always reset the socket to None after being closed)
        if (self._socket is not None):
            logging.error(self._name + " - Cannot reinitialize server socket.")
            raise RuntimeError(self._name + " - Cannot reinitialize server socket.  Try calling stop() first.")

        # Time to start the server
        logging.debug(self._name + " - Starting TCP Server")
        
        # Basic startup
        self._socket = socket.socket()
        
        # Set the commands so that the socket will allow immediate reuse of the port when closed.
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set the hostname and port to listen for incoming connections
        self._socket.bind((self.hostname, self.tcp_port))
        
        # Start listening for connections
        self._socket.listen(self.tcp_clients)
        logging.info(self._name + " - TCP Server listening on " + self.hostname + ":" + str(self.tcp_port))

        # Now we wait for connections and handle each one indefinitely (or until the kill switch is set)        
        while self._SOCKET_ALIVE:
            
            try:
                # Accept the new connection
                conn, address = self._socket.accept()
                logging.debug(self._name + " - " + str(address[0]) + ":" + str(address[1]) + " - CONNECT")
                
                # Send the welcome banner (App Name + Version + Daemon name)
                conn.sendall(str(kconfig.name+" v"+str(kconfig.version)+" [" + self._name + "]\n\n").encode())
                
                # Start the processor for incoming data exchange (request/response)
                self._processInbound(conn, address)
                
            except (KeyboardInterrupt): # Occurs when we press Ctrl+C on Linux
                
                # If we get a KeyboardInterrupt then let's try to shut down cleanly.
                # This isn't expected to be hit as the primary thread will catch the Ctrl+C command first
                
                logging.info(self._name + " - Ctrl+C detected.  Shutting down.")
                self.stop()  # Stop() is all we need to cleanly shutdown.  Will call child class's method first.
                
                return # Nice and neat closing
                
            except (OSError): # Occurs when we force close the listener on stop()
                
                pass    # this error will be raised on occasion depending on how the TCP socket is stopped
                        # so we put a simple "ignore" here so it doesn't fuss too much.
                
    def sendTCPCommand(self, s_in, hostname=None, tcp_port=None, s_type="plain"):
        """Simple method to send commands to a specified host/port"""
        
        # If no hostname is supplied in the function call then attempt to use the initialized one
        if (hostname is None):
            if (self.hostname is not None):
                hostname = self.hostname
            else:
                # If neither this function nor the class has a value then default to localhost
                hostname = "localhost"
            
        # If no port is supplied in the function call then attempt to use the initalized one.
        if (tcp_port is None):
            if (self.tcp_port is not None):
                tcp_port = self.tcp_port
            else:
                # Oops, we didn't get one in the function call and the class doesn't have one set.
                raise RuntimeError("Invalid tcp port specified.")

        # Prep the payload for sending.  Here we set the Content-Type
        if (s_type.strip().lower()=="json"):
            s_in = "Content-Type: JSON\n\n" + s_in.strip()
        else:
            # All values in the TYPE field that are not specifically known go here (so if not JSON then Text)
            s_in = "Content-Type: Text\n\nCOMMAND " + s_in.strip()
        
        # Payload set in "s_in" so now to send it to the target.
        
        # Create a socket
        s = socket.socket()
        
        # Connect to the target
        s.connect((hostname, tcp_port))
        
        # Get the welcome banner
        s.recv(1024).decode().strip() # Banner
        
        # Send the payload
        s.sendall(s_in.encode())
        
        # Get the result
        data = s.recv(1024)
        
        # Decode the resulting BYTE to STRING
        text = data.decode()
        
        # Process the response.
        if s_type == "json":
            text = text.strip() # return everything in JSON
        else:
            sp = text.strip().split("\n")
            if len(sp) > 0:
                text = sp[len(sp)-1] # One liners for TEXT
        
        # Shutdown the socket (proper protocol) 
        s.shutdown(0) # No, we aren't expecting to send or receive any more
        
        # Close the socket
        s.close()
        
        # Send the response back to the caller
        return text
        
    def stop(self):
        """Stop the Daemon
        
        This is necessary to be called via super().stop() at the end of an overridden child function"""
        
        logging.debug(self._name + " - Stopping TCP Server")
        
        # Just in case someone calls "stop" before "run"
        if self._socket is not None:
            
            # Force the socket server to shutdown
            self._socket.shutdown(0)
            
            # Close the socket
            self._socket.close()
            
            # Clear the socket object for re-use
            self._socket = None
        
        # Reset the kill switch
        self._SOCKET_ALIVE = False
        
        logging.debug(self._name + " - TCP Server stopped")
        
class Brain(Daemon):
    """Brain Daemon
    
    The centralized collector/processor for all data
    retrieved or provided by the other daemons.  Like
    the real world version of humans, every thought
    goes through the brain."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # Make sure to initialize the TCP Server values
        
        self._name = "BRAIN" # Update the name for logging
        
        # Initialize Local Values
        self.tcp_port = kwargs["brain_port"]
        self.hostname = kwargs["brain_ip"]
        
    def processCommand(self, s_in, s_type="text"):
        """Process incoming Commands/Data
        
        This is the main task of the brain which is to receive 
        and send communication to all the peripherals."""
        
        # Check the incoming request type
        #====================================
        # JSON processing
        
        if (s_type.lower().strip() == "json"):
            
            try:
                data = json.loads(s_in)
                
                if str(data["command"]).lower().strip() == "watcher_data":
                    
                    logging.debug(self._name + " - WATCHER_DATA command received.")

                    #TODO: Save this data
                                        
                    return json.dumps({ "error": False, "message": "OK" })
                    
                elif str(data["command"]).lower().strip() == "kill_all":
                    logging.info(self._name + " - KILL_ALL command received.")
                    
                    ret = self.shutdown()
                    if (ret == "OK"):
                        return json.dumps({ "error": False, "message": "OK" })
                    else:
                        return json.dumps({ "error": True, "message": ret })
                
            except:
                return json.dumps({ "error": True, "message": "Error parsing JSON request" })
        
        
            # End of JSON type processing    
            return super().processCommand(s_in, s_type)


        #====================================
        # Text processing (default so if we got to this point we are assuming text)
        
        if s_in.strip().lower() == "start_listening":
            
            # START_LISTENING command in the brain needs to be resent to the Listener.
            
            logging.info(self._name + " - START_LISTENING command received.")
            return self.sendTCPCommand(s_in, self._kwargs["listener_ip"], self._kwargs["listener_port"])

        elif s_in.strip().lower() == "stop_listening":
            
            # STOP_LISTENING command in the brain needs to be resent to the Listener.
            
            logging.info(self._name + " - STOP_LISTENING command received.")
            return self.sendTCPCommand(s_in, self._kwargs["listener_ip"], self._kwargs["listener_port"])
            return "OK"
        
        elif s_in.strip().lower() == "start_visualizer":
            
            # START_VISUALIZER command in the brain needs to be resent to the Speaker.
            
            logging.info(self._name + " - START_VISUALIZER command received.")
            return self.sendTCPCommand(s_in, self._kwargs["speaker_ip"], self._kwargs["speaker_port"])
            return "OK"

        elif s_in.strip().lower() == "stop_visualizer":
            
            # STOP_VISUALIZER command in the brain needs to be resent to the Speaker.
            
            logging.info(self._name + " - STOP_VISUALIZER command received.")
            return self.sendTCPCommand(s_in, self._kwargs["speaker_ip"], self._kwargs["speaker_port"])
            return "OK"

        elif s_in.strip().lower() == "start_watching":
            
            # START_WATCHING command in the brain needs to be resent to the Watcher.
            
            logging.info(self._name + " - START_WATCHING command received.")
            return self.sendTCPCommand(s_in, self._kwargs["watcher_ip"], self._kwargs["watcher_port"])
            return "OK"

        elif s_in.strip().lower() == "stop_watching":
            
            # STOP_WATCHING command in the brain needs to be resent to the Watcher.
            
            logging.info(self._name + " - STOP_WATCHING command received.")
            return self.sendTCPCommand(s_in, self._kwargs["watcher_ip"], self._kwargs["watcher_port"])
            return "OK"

        elif len(s_in) > 4 and s_in[:4].strip().lower() == "say":
            
            # SAY command in the brain needs special attention.            
            logging.info(self._name + " - SAY command received.")
            return self.say(s_in[4:].strip().lower())
        
        elif len(s_in) > 12 and s_in[:12].strip().lower() == "speech_input":
            
            # This only comes from the Listener and is SPEECH-TO-TEXT processed string data
            
            logging.debug(self._name + " - SPEECH_INPUT command received.")
            
            
            # Get the "text" part (removing the SPEECH_INPUT header)
            txt = s_in[12:].strip()
            
            # Check for keyword of "POWER DOWN" or "PLEASE POWER DOWN"
            if (len(txt) >= 10) and (len(txt) <= 17):  # please power down or just power down should work
                if txt[len(txt)-10:].lower() == "power down":
                    
                    # Politely notify user their command was received.
                    self.say("As you wish. Have a good "+ks.dayPart()+".")
                    
                    # Setting the shutdown command in its own thread so we can 
                    # return to the caller (Listener) that the audio_out message was processed.
                    threading.Thread(target=self.shutdown).start()
                    
                    # Notify caller that the message was completed successfully.
                    return "OK"
            
            
            #======================================
            
            
            #TODO: Process input to determine WHAT to say.  Echo mode right now.
            
            # Echo whatever we heard.
            self.say(s_in[12:].strip().lower())
            
            
            
            # When complete, return "OK"
            return "OK"
            
        elif s_in.strip().lower() == "kill_all":
            # In the brain, if we get a kill_all command then we will try to shut down everything.
            
            logging.info(self._name + " - KILL_ALL command received.")
            return self.shutdown()

        # Passthru in the event we didn't understand the incoming command send it to the parent class for processing.            
        return super().processCommand(s_in, s_type)
        
    def say(self, s_in):
        """The Brain's Processing of a Speech Command
        
        Simply put we need to notify the listner so we don't listen to our own speech
        and we need to send the words to the speaker to be spoken."""
        
        # First up, if we didn't get anything then don't do anything.
        if (s_in != ""):
            
            ## What happens if we can't connect!
            try:
                resp1 = self.sendTCPCommand("audio_out_start", self._kwargs["listener_ip"], self._kwargs["listener_port"])
            except ConnectionRefusedError:
                # On connection error we assume the Listener is either offline or never started
                logging.debug(self._name + " - LISTENER connection refused for AUDIO_OUT_START")
                resp1 = "OK"
                
            # Only speak if listener is successfully told not to listen right now
            if (resp1.strip().lower() == "ok"):
                
                # Why?  Even if the brain accounts for its "say" command, the listener may end up
                # with a longer utterence that started during the speech output which is not good.
                
                # Basically the listener would extend the frames of an utterence if speak continued
                # so you'd get the entire speech command back plus any additional utterence.
                
                # The only way to prevent this is to tell the listener the "exact" moment when we
                # are speaking and when we finish so it can cut those frames out of its capture.
                # NOTE: "exact" is not going to be perfect as we have network latency plus processing
                # overhead, but it should be close enough and is an acceptable method given the likelihood
                # of the problem being much more prevelant than missing a few milliseconds going this route.
                
                # Fully expect enhancements in this area in the future.
                
                resp2 = self.sendTCPCommand("say " + s_in, self._kwargs["speaker_ip"], self._kwargs["speaker_port"])
                
            # Tell the listener we are finished speaking
            try:
                resp3 = self.sendTCPCommand("audio_out_end", self._kwargs["listener_ip"], self._kwargs["listener_port"])
            except ConnectionRefusedError:
                # On connection error we assume the Listener is either offline or never started
                logging.debug(self._name + " - LISTENER connection refused for AUDIO_OUT_END")
                resp3 = "OK"

            ## What happens if we can't connect!
            
            # Process if we were actually successful or not (I really hope we were)
            if (resp1.strip().lower() == "ok" and resp2.strip().lower() == "ok" and resp3.strip().lower() == "ok"):
                return "OK"
            else:
                return "FAIL"
        
        # We shouldn't actually reach this "OK" statement, but just 
        # in case only successful messages should make it this far.
        return "OK"
        
    def shutdown(self):
        """Terminates all of Karen's functions."""
        
        # Shutdown Listener
        try:
            logging.debug(self._name + " - LISTENER attempting to shut down")
            
            # Send the command to the Listener Daemon
            listener_resp = self.sendTCPCommand("kill", self._kwargs["listener_ip"], self._kwargs["listener_port"])
            
            # If we got a response then we're probably all set but just to be sure we'll check the response code.
            if (listener_resp.strip().lower() != "ok"):

                # Not doing anything special here if it isn't okay other than just logging it and moving on.
                if (listener_resp != ""):
                    listener_resp = " (" + listener_resp + ")"

                logging.error(self._name + " - LISTENER failed to shut down" + listener_resp)
        except ConnectionRefusedError:
            # Connection Errors likely mean the Daemon was already shut down so we'll ignore it as an issue.
            logging.error(self._name + " - LISTENER appears to not be running")
                
        # Shutdown Speaker
        try:
            logging.debug(self._name + " - SPEAKER attempting to shut down")
            
            # Send the command to the Speaker Daemon
            speaker_resp = self.sendTCPCommand("kill", self._kwargs["speaker_ip"], self._kwargs["speaker_port"])
            
            # If we got a response then we're probably all set but just to be sure we'll check the response code.
            if (speaker_resp.strip().lower() != "ok"):

                # Not doing anything special here if it isn't okay other than just logging it and moving on.
                if (speaker_resp != ""):
                    speaker_resp = " (" + speaker_resp + ")"

                logging.error(self._name + " - SPEAKER failed to shut down" + speaker_resp)
        except ConnectionRefusedError:
            # Connection Errors likely mean the Daemon was already shut down so we'll ignore it as an issue.
            logging.error(self._name + " - SPEAKER appears to not be running")
            
        # Shutdown Watcher
        try:
            logging.debug(self._name + " - WATCHER attempting to shut down")
            
            # Send the command to the Watcher Daemon
            watcher_resp = self.sendTCPCommand("kill", self._kwargs["watcher_ip"], self._kwargs["watcher_port"])
            if (watcher_resp.strip().lower() != "ok"):

                # If we got a response then we're probably all set but just to be sure we'll check the response code.
                if (watcher_resp != ""):
                    watcher_resp = " (" + watcher_resp + ")"

                logging.error(self._name + " - WATCHER failed to shut down" + watcher_resp)
        except ConnectionRefusedError:
            # Connection Errors likely mean the Daemon was already shut down so we'll ignore it as an issue.
            logging.error(self._name + " - WATCHER appears to not be running")
            
        
        # Where is the KILL for the BRAIN daemon?  Well, you're in it so we will just kill the local TCP server
        # and to do that we just all the process command's standard "kill" process.
        return super().processCommand("kill", "text")
        
class Listener(Daemon):
    """Speech Capture Daemon
    
    In its human counterpart this Daemon would be equivalent to
    the ears and hearing process.  Primary purpose is to hear
    what is going on via a microphone using speech-to-text
    processing."""    
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        self._name = "LISTENER"
        
        # Initialize Local Values
        self.tcp_port = kwargs["listener_port"]
        self.hostname = kwargs["listener_ip"]
        
        self._audio_device = None           # The pyAudio() device for listening.  In other words, the Microphone

        self._isAudioOut = False            # Indicates if routine is actively pushing output to audio device.
                                            # Used to prevent the loop of listening to itself
                                            
        self._threadListening = None        # Stores local thread pointer for the listener.  The single focus
                                            # of this thread is to capture/convert to text the incoming speech.
                                            # This thread will then spawn the _threadProcessRaw to do the 
                                            # processing of what it hears.

        self._threadProcessRaw = None       # Stores local thread pointer for processing incoming speech as a 
                                            # separate thread in order to avoid blocking the listening queue
                                            
        self._input=[]                      # Stores last 10 items recognized as speech (most recent at end)

        self._KILL_SWITCH = False           # Switch used to determine if threads should be allowed to end.  
                                            # (True = KILL; False = Run)
                                            
        self.FORMAT = pyaudio.paInt16       # Default audio format
        
        self.CHANNELS = 1                   # This is set as a requirement for VAD and thus not configurable by user.
                                            # Input can only have a single channel.
                                            
        self.RATE = 16000                   # Input for VAD (required and thus hardcoded)

        self.BLOCKS_PER_SECOND = 50         # This is a magic number.  It is arbitrary as far as I can tell.
        
        # Of input device ... may need to resample audio
        self.RATE_INPUT = int(kwargs["input_rate"])        

        # Device index for microphone or recording device
        self.INPUT_DEVICE = kwargs["input_device"]

        # Magic number for padding between speech frames 
        # How long does the silence have to be to start a new dictation.  
        # Note that this adds to the delay of responsiveness b/c it has 
        # to wait for that much silence before it bothers trying to transcribe... 
        # This means that when set to 1000 ms then there is an extra 1 sec 
        # longer delay before the spoken words are recognized.
        self.PADDING_MS = int(kwargs["padding_ms"])

        # Ratio of frames with speech to total frames for consideration
        # A value of 0.75 means 75% of frames must have speech as identified by VAD
        self.RATIO = kwargs["ratio"]  
                                 
        # Disables listener on initial startup (daemon will still start, but will not listen to audio stream)
        self.DISABLE_ON_START = kwargs["listener_silent"]

        # Computed variables
        
        # Computed samples per block per second on input mic
        self.CHUNK=int(self.RATE_INPUT / float(self.BLOCKS_PER_SECOND))     
        
        # Computed samples per block per second needed for VAD
        # BLOCK_SIZE would be used for resampling if needed (future)
        self.BLOCK_SIZE=int(self.RATE / float(self.BLOCKS_PER_SECOND))      
                                                                            
        # Calculate the length of frames in milliseconds
        self.FRAME_DURATION_MS = 1000 * self.BLOCK_SIZE // self.RATE        
        
        # Calculate the number of frames to meet the padding milliseconds 
        self.NUM_PADDING_FRAMES = self.PADDING_MS // self.FRAME_DURATION_MS 
        
        # Set up C lib error handler for Alsa programs to trap errors from Alsa spin up
        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        
        # Buffer queue for incoming frames of audio
        #self._buffer_queue = queue.Queue()
        
        # Create Voice Activity Dectector and initialized with aggressiveness of filtering out audio noise.
        # Allowable values for aggressiveness are 0 thru 3.
        self._vad = webrtcvad.Vad(kwargs["vad_aggressiveness"])

        # Deep speech model file is a required value.  It's used to process frames of audio into text.
        self.MODEL_FILE = kwargs["speaker_model"]

        # DeepSpeech model object initialization
        # NOTE: For some reason the deepspeech binary outputs the version of deepspeech and tensorflow
        # and there doesn't seem to be a better way to stop this from writing to stderr.
        with SilenceStream(sys.stderr, log_file=kwargs["log_file"]):
            self._model = deepspeech.Model(self.MODEL_FILE)
        
        # According to deepspeech docs, the external scoring file setting is optional.        
        if (kwargs["scorer"] is not None):
            self.SCORER_FILE = kwargs["scorer"]
            self._model.enableExternalScorer(self.SCORER_FILE)
    
    @threaded
    def _processRawInput(self, raw_text):
        """Processes raw converted speech input using a separate thread."""

        # Send speech to the brain for processing (and output if appropriate)
        logging.debug(self._name + " - Sending to Brain: " + raw_text)
        self.sendTCPCommand("speech_input " + raw_text, self._kwargs["brain_ip"], self._kwargs["brain_port"])

    @threaded
    def _read_from_mic(self):
        """Opens audio device for listening and processing speech to text"""
 
        buffer_queue = queue.Queue()    # Buffer queue for incoming frames of audio
        self._KILL_SWITCH = False       # Reset to False to insure we can successfully start

        def proxy_callback(in_data, frame_count, time_info, status):
            """Callback for the audio capture which adds the incoming audio frames to the buffer queue"""
            
            # Save captured frames to buffer
            buffer_queue.put(in_data)
            
            # Tell the caller that it can continue capturing frames
            return (None, pyaudio.paContinue)

        # Using a collections queue to enable fast response to processing items.
        # The collections class is simply faster at handling this data than a simple dict or array.
        # The size of the buffer is the length of the padding and thereby those chunks of audio.
        ring_buffer = collections.deque(maxlen=self.NUM_PADDING_FRAMES)

        # If the audio device is not already initialized then initialize it now        
        if (self._audio_device is None):
            self._audio_device = pyaudio.PyAudio()
        
        # Open a stream on the audio device for reading frames
        stream = self._audio_device.open(format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE_INPUT,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=self.INPUT_DEVICE,
            stream_callback=proxy_callback)
        
        stream.start_stream()                               # Open audio device stream
        
        stream_context = self._model.createStream()         # Context of audio frames is used to 
                                                            # better identify the spoken words.
        
        triggered = False                                   # Used to flag whether we are above
                                                            # or below the ratio threshold set
                                                            # for speech frames to total frames
        
        logging.debug(self._name + " - Listener started")
        
        # We will loop looking for incoming audio until the KILL_SWITCH is set to True
        while self._KILL_SWITCH == False:

            # Get current data in buffer as an audio frame
            frame = buffer_queue.get()

            # A lot of the following code was pulled from examples on DeepSpeech
            # https://github.com/mozilla/DeepSpeech-examples/blob/r0.7/mic_vad_streaming/mic_vad_streaming.py
            
            # Important note that the frame lengths must be specific sizes for VAD detection to work.
            # Voice Activity Detection (VAD) also expects single channel input at specific rates.
            # Highly recommend reading up on webrtcvad() before adjusting any of this.
            
            # We also skip this process if we are actively sending audio to the output device to avoid
            # looping and thus listening to ourselves.
            if len(frame) >= 640 and self._isAudioOut == False:
                
                # Bool to determine if this frame includes speech.
                # This only determines if the frame has speech, it does not translate to text.
                is_speech = self._vad.is_speech(frame, self.RATE_INPUT)
            
                # Trigger is set for first frame that contains speech and remains triggered until 
                # we fall below the allowed ratio of speech frames to total frames

                if not triggered:

                    # Save the frame to the buffer along with an indication of if it is speech (or not)
                    ring_buffer.append((frame, is_speech))

                    # Get the number of frames with speech in them
                    num_voiced = len([f for f, speech in ring_buffer if speech])

                    # Compare frames with speech to the expected number of frames with speech
                    if num_voiced > self.RATIO * ring_buffer.maxlen:
                        
                        # We have more speech than the ratio so we start listening
                        triggered = True

                        # Feed data into the deepspeech model for determing the words used
                        for f, s in ring_buffer:
                            stream_context.feedAudioContent(np.frombuffer(f, np.int16))

                        # Since we've now fed every frame in the buffer to the deepspeech model
                        # we no longer need the frames collected up to this point
                        ring_buffer.clear()
            
                else:
                    
                    # We only get here after we've identified we have enough frames to cross the threshold
                    # for the supplied ratio of speech to total frames.  Thus we can safely keep feeding
                    # incoming frames into the deepspeech model until we fall below the threshold again.
                    
                    # Feed to deepspeech model the incoming frame
                    stream_context.feedAudioContent(np.frombuffer(frame, np.int16))

                    # Save to ring buffer for calculating the ratio of speech to total frames with speech
                    ring_buffer.append((frame, is_speech))
                    
                    # We have a full collection of frames so now we loop through them to recalculate our total
                    # number of non-spoken frames (as I pulled from an example this could easily be stated as
                    # the inverse of the calculation in the code block above)
                    num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                    # Compare our calculated value with the ratio.  In this case we're doing the opposite
                    # of the calculation in the previous code block by looking for frames without speech
                    if num_unvoiced > self.RATIO * ring_buffer.maxlen:
                        
                        # We have fallen below the threshold for speech per frame ratio
                        triggered = False
                        
                        # Let's see if we heard anything that can be translated to words.
                        # This is the invocation of the deepspeech's primary STT logic.
                        # Note that this is outside the kill_switch block just to insure that all the
                        # buffers are cleaned and closed properly.  (Arguably this is not needed if killed)
                        text = str(stream_context.finishStream())

                        # We've completed the hard part.  Now let's just clean up.
                        if self._KILL_SWITCH == False:
                            
                            # We'll only process if the text if there is a real value AND we're not already processing something.
                            # We don't block the processing of incoming audio though, we just ignore it if we're processing data.
                            if text.strip() != "" and (self._threadProcessRaw is None or self._threadProcessRaw.isAlive() == False):

                                logging.debug(self._name + " - Heard: " + text)
                                
                                # Save the input to the history
                                self._input.append(text)

                                # If we have more than 10 entries then throw away the oldest entry.
                                if (len(self._input) > 10):
                                    self._input.pop(0)

                                # Start a thread for processing the parsed text.
                                # Using a thread here to prevent blocking of listening.
                                self._threadProcessRaw = self._processRawInput(text)

                            stream_context = self._model.createStream() # Create a fresh new context

                        ring_buffer.clear() # Clear the ring buffer as we've crossed the threshold again

        logging.debug(self._name + " - Stopping streams")        
        stream.stop_stream()                          # Stop audio device stream
        stream.close()                                # Close audio device stream
        logging.debug(self._name + " - Streams stopped")

    def _startListening(self):
        """Starts a thread for listening to the audio device."""

        self._isAudioOut = False    # Resetting this for the time being although it is possible
                                    # That we start it within a voice loop.  But it should only
                                    # repeat itself once. 
                                    # Resetting this allows for the unlikely event that a
                                    # audio_out_end was not received properly.

        # Effectively drop this request if there is already a thread running for listening.        
        if (self._threadListening is not None) and (self._threadListening.isAlive()):
            logging.debug(self._name + " - Listener already started.")
            return False
            
        logging.info(self._name + " - Starting listener")
        
        # Start up the thread and store it for when we need to stop listening
        self._threadListening = self._read_from_mic()
        
        return True # Um, sure.  This will never "error".


    def _stopListening(self):
        """Stops listening by setting the kill switch."""
        
        logging.debug(self._name + " - Stopping listener")

        # Enable the KILL SWITCH (which will force the loop to end)
        self._KILL_SWITCH = True
        logging.debug(self._name + " - Kill switch set")

        # Once the KILL SWITCH is set all we need to do is wait for the thread to complete.
        if self._threadListening is not None and self._threadListening.isAlive():
            logging.debug(self._name + " - Awaiting thread joining")
            self._threadListening.join() # And we wait for it to join
            self._threadListening = None # And reset in case we want to "startListening()" again
            logging.info(self._name + " - Listener stopped")
        else:
            logging.debug(self._name + " - Listener not running")
        
        return True # Not a whole lot could go wrong here. (hahaha)
        
    def destroy(self):
        """Destroys the initialized audio device"""

        # Only need to tear this down if the device was initialized
        if (self._audio_device is not None):
            
            # We should only allow a destroy process on a killed/stopped listener.        
            if (self._KILL_SWITCH == False):
                logging.error(self._name + " - stopListening() must be called prior to destroying the object.")
                return
                
            # If kill switch is set then we just need to wait for it to end.
            if (self._threadListening is not None):
                self._threadListening.join()
        
            # Here we're waiting in the event that some command is still being processed.
            if (self._threadProcessRaw is not None):
                self._threadProcessRaw.join()

            # Nice and neat cleanup.  Just the way mom taught us.
            self._audio_device.terminate()
            self._audio_device = None

    def isAlive(self):
        """Determines if any threads are active in this class."""
        
        # If we're not listening and we're not outputing anything then we should be safe that at least 
        # the main threads are not active.
        if self._threadListening is None and self._threadProcessRaw is None and self._isAudioOut == False:
            return False
        
        # If we're playing audio then it appears safe that we are alive.
        # Since this is the only logic in the "say" command it seems reasonable even for external calls, 
        # but ideally the external callers will manage the thread handles themselves.  
        if self._isAudioOut:
            return True

        # Is the class currently listening for input
        if self._threadListening is not None and self._threadListening.isAlive():
            return True
        
        # Is the class currently processing a response
        if self._threadProcessRaw is not None and self._threadProcessRaw.isAlive():    
            return True
            
        # If we can't prove we are alive then we probably aren't
        return False

    def run(self):
        """The main thread runtime for the Daemon.
        
        Will continue running until listener is stopped or thread fails."""
        

        # Unless explicitly told to not start, we will begin listening automatically.
        if (self.DISABLE_ON_START != True):
            
            # We may not yet have an audio device object so let's check to be sure.
            if (self._audio_device is None):
                self._audio_device = pyaudio.PyAudio() # Initialize object


            # And here is where the magic happens!  Careful what you say from this point on.
            self._startListening()
            
            
        #=========================
        # Now let's start up the TCP Server so we can get those external commands.
        
        # This is very important or else all the other items here will abort since they
        # are not on the main thread.  Only the TCP server runs on the main thread.
        super().run()
        

    def stop(self):
        """Stops the entire listener and releases all devices and resources."""
        
        # Check and be sure we aren't still listening for audio.
        if self._threadListening is not None and self._threadListening.isAlive():
            # Looks like we are listing to audio streams.  Let's kill that now.
            self._stopListening()

        # Now to free up the audio device for other users (clean shutdown)
        self.destroy()

        # And let's be sure we stop the TCP server that's keeping the daemon alive.
        super().stop()
            
    def processCommand(self, s_in, s_type="text"):
        """Process incoming Commands/Data
        
        The main task of the listener is to listen to audio, convert it to 
        text, and send it to the brain for further processing."""
        
        if (s_type.lower().strip() == "json"):
            
            # What's this JSON stuff.  We don't understand that!  Send to the parent class for default processing.
            return super().processCommand(s_in, s_type)
        
        if s_in.lower() == "audio_out_start":
            
            # AUDIO_OUT_START means the speaker is getting ready to say something so we should 
            # stop listening briefly so as to not listen to our own speach and create a loop.
            
            logging.debug(self._name + " - AUDIO_OUT_START received.")
            self._isAudioOut = True
            return "OK"
        
        elif s_in.lower() == "audio_out_end":
            
            # AUDIO_OUT_END means the speaker is finished speaking so we can safely start 
            # listening again without fear of looping.
            
            logging.debug(self._name + " - AUDIO_OUT_END received.")
            self._isAudioOut = False
            return "OK"
                
        elif s_in.lower() == "start_listening":
            
            # START LISTENER (if not already running)
            
            logging.info(self._name + " - START_LISTENING command received.")
            
            # If we're already alive we don't need to do anything
            if self.isAlive():
                return "ERROR Already listening"
            
            # Guess we aren't alive so let's try to start
            if self._startListening():
                return "OK"
            else:
                return "ERROR Could not start listener" # Uh oh, something went wrong!
            
        elif s_in.lower() == "stop_listening":

            # STOP LISTENER (if running)
            
            logging.info(self._name + " - STOP_LISTENING command received.")
            
            # No point in trying to stop if we aren't alive.
            if self.isAlive():
                
                # End the Gossip already!
                if self._stopListening():
                    return "OK"
                
            return "ERROR Listener not running"
       

        # VERY Important.  Always call the parent processCommand to account for KILL commands!
        return super().processCommand(s_in, s_type)
        
class Speaker(Daemon):
    """The Audible Voice Daemon
    
    The quintessential chatterbox and most comparible to its
    flesh relatives as the mouth, vocal chords, and related tissue.
    
    In other words, this is the part that talks."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._name = "SPEAKER"
        
        # Initialize Local Values
        self.tcp_port = kwargs["speaker_port"]
        self.hostname = kwargs["speaker_ip"]

        # Visualizer process ID (used to kill it on stop() calls)
        self._visualizer = None
        self.visualizerCommand = kwargs["speaker_visualizer"]   # This is ideally an array of shell commands/vars
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
        

        self._isAudioOut = False    # Indicates if audio is currently being sent to the output device
        
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

        # This isn't a critical function so we'll pretend like everything is great.
        return True
    
    def _stopVisualizer(self):
        """Stop the visualizer.  (Who needed that anyway.)
        
        Note that this is only for a reactive display of the audio while it is being spoken.  It's just
        a visual effect.  It has no real value to the overall code."""
        
        # Do we have something to kill?
        if (self._visualizer is not None):
            # Okay, let's try not to break too many things in our operating system.        
            os.killpg(os.getpgid(self._visualizer.pid), sig.SIGTERM)  # Just kill our subprocess's page
            self._visualizer.terminate() # Now kill the subprocess itself
            self._visualizer.wait() # Now wait for all that to finish processing
            self._visualizer = None # And reset so we can do it all over again.
            logging.info(self._name + " - Visualizer stopped")
        else:
            logging.debug(self._name + " - Visualizer not running")
        
        # Yep, another one of those really important return values that is totally dependent on what we just did.
        return True

    def _tts(self, text):
        """Converts text into synthesized speech."""
        
        self._isAudioOut = True # Just an indicator... doesn't really do anything.

        logging.info(self._name + " - Saying: " + text)
        
        # The os.system() call is a blocking call so it will fully execute the command before progressing
        # so we're pretty safe without having to do anything fancy to trap when we're sending audio output.
        
        #FIXME: The text variable can have characters that create a massive security risk here.  We should clean this up.
        os.system("echo \"%s\" | festival --tts" % text.replace("`","'").replace('"',"'").replace("\n"," ").replace("\\","\\\\").replace("%"," percent "))

        self._isAudioOut = False # For consistency, we'll keep updating this useless indicator.
    
    def processCommand(self, s_in, s_type="text"):
        """Process incoming Commands/Data
        
        The main task of the speaker is to perform text-to-speech and then 
        send audio to the output device.  That means this is one of the 
        more simple Daemons."""
        
        if (s_type.lower().strip() == "json"):
            # We don't need no stinkin' JSON in here!
            return super().processCommand(s_in, type)
        
        if len(s_in) > 4 and s_in[:4].strip().lower() == "say":
            # Simple SAY command received.  Cuts off SAY{space} on the front and treats everything else as what to speak.
            
            logging.debug(self._name + " - SAY command received.")
            
            # Send to our TEXT-TO-SPEECH command.
            self._tts(s_in[4:].strip())
            
            # Yep, another guaranteed success
            return "OK"
        
        elif s_in.lower() == "start_visualizer":
            
            # Let's try to make things pretty with a visualizer
            if self._startVisualizer():
                return "OK"
            else:
                return "ERROR Visualizer already running"  # Oops.  Somebody called the same process too many times. 

        elif s_in.lower() == "stop_visualizer":
            
            if self._stopVisualizer():
                return "OK"
            else:
                return "ERROR Visualizer not running" # Or it could be it failed to be stopped and is taking over the world.
        
        # VERY Important.  We must call our parent class process command to handle KILL events.
        return super().processCommand(s_in, s_type)
    
    def run(self):
        """Kicks off the main thread runtime for the Daemon.
        
        Will continue running until speaker is stopped or thread fails."""
        
        # We automatically try to start the visualizer if a command is present.
        if self.visualizerCommand is not None and str(self.visualizerCommand).strip() != "": 
            self._startVisualizer()
            
        # Start up the TCP server and wait for it to be killed.
        super().run()
        
    def stop(self):
        """Stops the entire speaker daemon and releases all devices and resources."""
        
        # Kill the subprocess if it isn't already killed.
        self._stopVisualizer()

        # Stop the TCP Server parent process
        super().stop()
    
class Watcher(Daemon):
    """The Vision/Eyes Daemon
    
    This daemon provides the gift of sight to the project."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._name = "WATCHER"
        
        # Initialize Local Values
        self.tcp_port = kwargs["watcher_port"]
        self.hostname = kwargs["watcher_ip"]
        
        # Video Device Index
        self.VIDEO_DEVICE_ID = kwargs["watcher_device"]

        # Model for object recognition (e.g. Faces)
        self.MODEL_FILE = kwargs["watcher_model"]
        
        # Model for recognizing the objects that were detected.
        # e.g. Who's face it is that we're looking at.
        self.TRAINED_FILE = kwargs["watcher_trained"]
        
        # Watcher FPS determines the number of frames per second that we
        # want to process for incoming objects.  Since this is video
        # the FPS can be as high as the device/hardware supports
        # but in reality our view of the world doesn't need to
        # process every frame to know what we're seeing.
        
        # I'd recommend keeping  this around 1 to 2 frames per second at a max.
        
        if (kwargs["watcher_fps"] is None):
            self.FPS = float(1) # Default to 1 frame per second
        else:
            self.FPS = float(kwargs["watcher_fps"]) # Set based on input
            
        # If the video device is mounted incorrectly it may need to be rotated.
        # This is especially true in some of the Raspberry Pi applications.
        # Options are:
        #    90 ... to rotate 90 degrees clockwise
        #    -90 ... to rotate 90 degrees counterclockwise
        #    180 ... to essentially flip the image (rotate 180 degrees)
        self.rotate = kwargs["watcher_rotate"]
        
        self._video_device = None       # Video Device Object (so we don't keep recapturing when not needed)
        self.DISABLE_ON_START = False   # Disable video capture on initialization
        self._KILL_SWITCH = True        # Kill Switch that breaks the video stream when shutting down
        self._threadWatching = None     # Thread for capturing video frames
        self._threadManager = None      # Thread for managing the thread pool for sending info to the Brain
        self._OFFLINE = False           # Indicates if the brain is offline (unable to connect)
        
        self._dataset = None            # Our trained data set of faces (who belongs to which face)
        
        # The face detection model (to identify all faces (known/unknown) in a video framez
        # https://github.com/opencv/opencv/tree/master/data
        self._model = cv2.CascadeClassifier(self.MODEL_FILE);
        
        # Thead array for active threads (sending TCP messages to brain)
        self._threads = []
        

    @threaded
    def _manageThreads(self):
        """Thread pool manager for removing threads from the array when they complete."""
        
        # Why?  If we don't manage our array then we'll keep adding new threads and consume
        # more memory than is required.  Managing this array keeps it to a relatively slow
        # burn rate and does a bit of our own garbage collection
        #
        # If we didn't do this then imagine a list of old, current, and new threads that has
        # more than 100,000 entries in it with 99,995 all being dead/completed.  So we avoid
        # this situation in the _manageThreads() process (that is itself a thread) 
        
        # We run until the global kill switch is set.
        while self._KILL_SWITCH == False:
            
            # We start at the last thread and work our way backward.  This allows us to delete
            # an array entry without breaking our iterator... and yes, I'm sure there is a better
            # way to do this than is shown here.
            
            i = len(self._threads) - 1
            while i >= 0:
                
                # Simple check to see if the thread is alive.
                if self._threads[i].isAlive() == False:
                    
                    # If thread is dead then we don't need it any more.
                    self._threads.pop(i)
                    
                i = i - 1
            
            # We don't need to be too invasive on resources.  Once every few seconds should
            # be more than adequate for cleaning up dead threads.
            
            time.sleep(2)
    
    @threaded
    def _read_from_camera(self):
        """Primary goodness of the Wather Daemon.  
        
        Reads and processes the video frames through our model
        and recognizer."""
        
        # Reset our kill switch so that we have a nice clean start.
        self._KILL_SWITCH = False
        
        if self._threadManager is None:
            self._threadManager = self._manageThreads()

        # Initialize the recognizer for determining the specifics behind the object detected.  
        # (e.g. Who's face it is that we detected)
        # Putting this here so we can restart the watcher to refresh the trained data set
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(self.TRAINED_FILE)  # Load our trained data set

        # Run until killed        
        while self._KILL_SWITCH == False:
            
            # Get a frame from the video device (yes, just one frame)
            ret, im = self._video_device.read()
            
            # See if we need to rotate it and do so if required
            if self.rotate is not None:
                if str(self.rotate).upper() == "ROTATE_90_CLOCKWISE":
                    im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
                elif str(self.rotate).upper() == "ROTATE_90_COUNTERCLOCKWISE":
                    im = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif str(self.rotate).upper() == "ROTATE_180": 
                    im = cv2.rotate(im, cv2.ROTATE_180)
            
            # Convert image to grayscale.  
            # Some folks believe this improves identification, but your mileage may vary.
            gray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
            
            # Detect faces (not the who... just if I see a face).
            # Returns an array for each face it sees in the frame.
            faces = self._model.detectMultiScale(gray, 1.2,5)
            
            # Since we care about all the faces we'll store them after they are processed in an array
            people = []
            
            # Iterate through the faces for identification.
            for (x,y,w,h) in faces:

                # Pull the ID and Distance from the recognizer based on the face in the image
                # Remember that "gray" is our image now so this is literally cutting out the face
                # at the coordinates provided and attempting to predict the person it is seeing.
                            
                Id = recognizer.predict(gray[y:y+h,x:x+w])

                # Let's build a JSON array of the person based on what we've learned so far.
                person = {
                        "id":Id[0],
                        "distance":Id[1],
                        "coordinates": {
                                "x":int(x),
                                "y":int(y)
                            },
                        "dimensions": {
                                "width":int(w),
                                "height":int(h)
                            }
                    }

                # And now we save our person to our array of people.
                people.append(person)
            
            # Send the list of people in the frame to the brain.
            # We do this on a separate thread to avoid blocking the image capture process.
            # Technically we could have offloaded the entire recognizer process to a separate 
            # thread so may need to consider doing that in the future.
            if (len(people) > 0):
                # We only send data to the brain when we have something to send.
                t = self.sendWatcherData(people)
                self._threads.append(t)
            
            # Here we are trying to read only 1 frame per the defined FPS setting (default to 1 per sec).
            # Standard NTSC is 30+ frames per second so this should significantly
            # reduce the load on the server.  It will also cut down on chatter to
            # the brain.
                
            t = time.time()
            while time.time() < (t+(1 // float(self.FPS))):
                # In order to process frames without delay we have to "grab" the data in
                # between our frame captures.  Seems strange, but it's needed.
                self._video_device.grab()
                    

    def _startWatching(self):
        """Starts a thread for watching to the video device."""
        
        # Check if we're already watching and if so then exit.
        if (self._threadWatching is not None) and (self._threadWatching.isAlive()):
            logging.debug(self._name + " - Watcher already started.")
            return False
        
        logging.info(self._name + " - Starting watcher")

        # Make sure we have a working video device
        if (self._video_device is None):
            self._video_device = cv2.VideoCapture(self.VIDEO_DEVICE_ID)

        # Start the video capture's thread for reference
        self._threadWatching = self._read_from_camera()
        
        # All set.  Don't you love how confident we are that the thread started successfully?
        return True
    
    def _stopWatching(self):
        """Stops/Kills the thread for watching to the video device."""
        
        logging.debug(self._name + " - Stopping watcher")

        # Set the kill switch which tells the read loop and the thread pool manager to end.
        self._KILL_SWITCH = True
        logging.debug(self._name + " - Kill switch set")

        # Now we wait for the thread to finish if it's still alive.
        if self._threadWatching is not None and self._threadWatching.isAlive():
            logging.debug(self._name + " - Awaiting thread joining")
            self._threadWatching.join() # Wait
            self._threadWatching = None # Reset so we can "startWatching" again without fear
            logging.info(self._name + " - Watcher stopped")
        else:
            logging.debug(self._name + " - Watcher not running")

        # Next, let's make sure all our TCP requests have been sent successfully.
        if self._threadManager is not None and self._threadManager.isAlive():
            self._threadManager.join()

        # Lastly, let's just doublecheck that any open threads are really finished.
        for x in self._threads:
            if x.isAlive():
                x.join()
        
        # Alright.  Looks like we can report success that everything is stopped.
        return True
    
    def isAlive(self):
        """Determines if any threads are active in this class."""

        # First, let's check the kill switch.  That's the easiest way to confirm if we're alive.        
        if self._KILL_SWITCH == False:
            return True
        
        # Next, let's make sure nothing funky is going on with our watching thread.
        if self._threadWatching is not None and self._threadWatching.isAlive():
            return True
        
        # And we'll check the thread manager to be sure it's dead (based on kill switch as well)
        if self._threadManager is not None and self._threadManager.isAlive():
            return True
        
        # Lastly, let's make sure anything left running is actually finished.
        for x in self._threads:
            if x.isAlive():
                return True

        # At this point it looks like everything is dead/not running so we can assume we're not alive.
        return False
    
    def run(self):
        """Kicks off the main thread runtime for the Daemon.
        
        Will continue running until watcher is stopped or thread fails."""
        
        # If we were were not disabled on start then we need to start listening.
        if self.DISABLE_ON_START == False:
            self._startWatching() # Starts its own thread
        
        # Start up the TCP Server
        super().run()
        
    def stop(self):
        """Stops the entire watcher daemon and releases all devices and resources."""
        
        # If we are watching then let's stop that now
        if self._threadWatching is not None and self._threadWatching.isAlive():
            self._stopWatching()
        
        # Release the video device
        if (self._video_device is not None):
            self._video_device.release()
            self._video_device = None

        # And now terminate the TCP server in parent class            
        super().stop()
        
    def processCommand(self, s_in, s_type="text"):
        """Process incoming Commands/Data
        
        The main task of the watcher is to perform object detection and then 
        send results to the brain."""
        
        if (s_type.lower().strip() == "json"):
            # No JSON commands expected for the watcher
            return super().processCommand(s_in, s_type)
        
        
        if s_in.lower() == "start_watching":

            # START LISTENER (if not already running)
            
            logging.info(self._name + " - START_WATCHING command received.")
            
            # Are we already alive?  If so we don't need to do anything.
            if self.isAlive():
                return "ERROR Already watching"
            
            # Let's attempt to start watching.
            if self._startWatching():
                return "OK"
            else:
                return "ERROR Watcher failed to start"
            
        if s_in.lower() == "stop_watching":
            
            # START LISTENER (if not already running)
            
            logging.info(self._name + " - STOP_WATCHING command received.")
            
            if self._stopWatching():
                return "OK"
            else:
                return "ERROR Watcher not running"
            
        if s_in.lower() == "train":
            
            #TODO: Add training for remote execution
            
            return "ERROR Invalid command"

        # At this point we don't understand the command so let's send to the parent class
        return super().processCommand(s_in, s_type)

    @threaded
    def sendWatcherData(self, data):
        """Simple thread used to send captured data to the brain"""
        
        #TODO: Consider keeping TCP open to reduce overhead since this will send new data at least every second depending on the FPS setting.
        
        # Let's build a json string for sending.
        j_data = json.dumps({ "command": "WATCHER_DATA", "data": data })

        try:
            # Attempt sending the data to the brain
            resp = self.sendTCPCommand(j_data, self._kwargs["brain_ip"], self._kwargs["brain_port"], s_type="json")

            self._OFFLINE = False       # If we were offline then now we know we aren't 
                                        # as the send command must be successful to reach 
                                        # this point.
            
            try:
                # Parse the response
                j_resp = json.loads(resp)
            
                # Check if we had an error on the brain (although we don't really care so much).
                if (j_resp["error"] == True):
                    logging.warning(self._name + " - " + str(j_resp["message"]))
            except:
                # Hmm... something bad happened here.
                logging.error(self._name + " - " + str(sys.exc_info()[0]))
                
        except ConnectionRefusedError:

            # It's possible the brain isn't running.  We should gracefully exit
            
            if (self._OFFLINE):
                # Logging this as DEBUG to keep down the continuous stream of failures when the brain goes offline.
                logging.debug(self._name + " - Failed to send data to Brain")
            else:
                # We will log the first connection error so that the user knows it did fail.
                logging.error(self._name + " - Failed to send data to Brain")
                self._OFFLINE = True # Set to offline until we get a packet sent successfully.

    def train(self):
        """Retrains the face recognition (the WHO) based on images supplied"""
        
        # Let's make sure we have a folder of images to process
        if self._kwargs["watcher_input_folder"] is None or os.path.exists(self._kwargs["watcher_input_folder"]) == False:
            logging.error(self._name + " - Invalid image input folder.")
            return False
        
        # And insure we now where we want to save the results
        if self.TRAINED_FILE is None:
            logging.error(self._name + " - Trained Data file not specified.")
            return False
        
        # And that we can actually detect faces in images
        if self.MODEL_FILE is None or os.path.exists(self.MODEL_FILE) == False:
            logging.error(self._name + " - Model file not found.")
            return False
        

        #================================================        
        # All set now... let's give it a go...
        logging.info(self._name + " - Training algorithm started.")
        
        # Create the recognizer (this is used to compare faces to identify individuals)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Get the list of images to process from the input folder.
        imagePaths = [os.path.join(self._kwargs["watcher_input_folder"],f) for f in os.listdir(self._kwargs["watcher_input_folder"])]
        
        # Set up a few arrays for capturing data
        faceSamples=[]
        ids = []

        # Loop through input images in the folder supplied.
        for imagePath in imagePaths:
            try:
                # Open the image as a resource
                PIL_img = Image.open(imagePath).convert('L')
                
                # Convert to Numpy Array
                img_numpy = np.array(PIL_img,'uint8')
                
                # Parse the filename (expected naming format is "user.{ID}.{number}.jpg")
                i_id = int(os.path.split(imagePath)[-1].split(".")[1])
                
                # At this point we should be okay to proceed with the image supplied.
                logging.debug(self._name + " - Training input: " + imagePath)
                
                # Let's pull out the faces from the image (may be more than one!)
                faces = self._model.detectMultiScale(img_numpy)
            
                # Let's make sure we only have one image per face
                if len(faces) > 1:
                    logging.error(self._name + " - Multiple faces detected in: " + imagePath)
                else:
                    # Loop through faces object for detection ... and there should only be 1. 
                    for (x,y,w,h) in faces:
                        
                        # Let's save the results of what we've found so far.
                        
                        # Yes, we are cutting out the face from the image and storing in an array.
                        faceSamples.append(img_numpy[y:y+h,x:x+w]) 
                        
                        # Ids go in the ID array.
                        ids.append(i_id)
            except:
                logging.error(self._name + " - Failed to process: " + imagePath)

        # Okay, we should be done collecting faces.
        logging.debug(self._name + " - Identified " + str(len(faceSamples)) + " sample from images")
        
        # This is where the real work happens... let's create the training data based on the faces collected.
        recognizer.train(faceSamples, np.array(ids))

        # And now for the final results and saving them to a file.
        logging.debug(self._name + " - Writing data to " + self.TRAINED_FILE)
        recognizer.save(self.TRAINED_FILE)
        
        logging.info(self._name + " - Training algorithm completed.")
        
        return True  # Yep, if we made it here then we're successful.