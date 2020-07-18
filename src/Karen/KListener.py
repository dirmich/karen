'''
Project Karen: Synthetic Human
Created on Jul 12, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: Listener Daemon

'''
import sys, logging
from .KHTTP import TCPServer, KHTTPRequest, JSON_request, JSON_response
from .KShared import py_error_handler, SilenceStream, threaded

import numpy as np
import pyaudio, queue, webrtcvad, collections
import deepspeech
from ctypes import CFUNCTYPE, cdll, c_char_p, c_int

import json

class Listener(TCPServer):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Daemon default name (make sure to always set this on inheritance!)
        self._name = "LISTENER"
        
        # TCP Command Interface
        self.tcp_port = kwargs["port"]            # TCP Port for listener.
        self.hostname = kwargs["ip"]     # TCP Hostname
        self.use_http = kwargs["use_http"]
        self.keyfile=kwargs["ssl_keyfile"]
        self.certfile=kwargs["ssl_certfile"]

        self.brain_ip=kwargs["brain_ip"]
        self.brain_port=kwargs["brain_port"]
        self.auto_register = True
        
        self._audio_device = None           # The pyAudio() device for listening.  In other words, the Microphone

        self._isAudioOut = False            # Indicates if routine is actively pushing output to audio device.
                                            # Used to prevent the loop of listening to itself
                                            
        self._Listener_thread = None        # Stores local thread pointer for the listener.  The single focus
                                            # of this thread is to capture/convert to text the incoming speech.
                                            # This thread will then spawn the _threadProcessRaw to do the 
                                            # processing of what it hears.

        self._input=[]                      # Stores last 10 items recognized as speech (most recent at end)

        self._Listener_running = False      # Switch used to determine if threads should be allowed to end.  
                                            # (True = Run; False = Die)
                                            
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
        self.DISABLE_ON_START = kwargs["silent"]

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
        
        # Buffer queue for incoming frames of audio
        #self._buffer_queue = queue.Queue()
        
        # Create Voice Activity Dectector and initialized with aggressiveness of filtering out audio noise.
        # Allowable values for aggressiveness are 0 thru 3.
        self._vad = webrtcvad.Vad(kwargs["vad_aggressiveness"])

        # Deep speech model file is a required value.  It's used to process frames of audio into text.
        self.MODEL_FILE = kwargs["model"]

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
    def _acceptConnection(self, conn, address):
        
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
                
            if (len(path) == 8 and path == "/control") or (len(path) > 8 and path[:9] == "/control/"):
                
                if "command" in payload:
                    my_cmd = str(payload["command"]).lower()
                    
                    if my_cmd == "kill":
                        
                        JSON_response(conn, { "error": False, "message": "Server is shutting down." })
                        #response_status = "200 OK"
                        #response_type = "application/json"
                        #response_body = json.dumps({ "error": False, "message": "Server is shutting down." })
                            
                        #response_text = "HTTP/1.1 "+response_status+"\nDate: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")+"\nContent-Type: "+response_type+"\nContent-Length: "+str(len(response_body)) + "\n\n"
                        #conn.send(response_text.encode())
                        #conn.send(response_body.encode())
                
                        #conn.shutdown(socket.SHUT_RDWR)
                        #conn.close()
            
                        self.stop()
                        return True
                        
                    elif my_cmd == "stop_listener":
                         
                        b = self.stopListening()
                        if b == True:
                            
                            JSON_response(conn, { "error": False, "message": "Listener stopped successfully." })
                            return True
                            #response_status = "200 OK"
                            #response_type = "application/json"
                            #response_body = json.dumps({ "error": False, "message": "Listener stopped successfully." })
                        else:
                            JSON_response(conn, { "error": True, "message": "Listener not running." })
                            return False
                            #response_status = "500 Internal Server Error"
                            #response_type = "application/json"
                            #response_body = json.dumps({ "error": True, "message": "Listener not running." })
                
                    elif my_cmd == "start_listener":
                        
                        b = self.startListening()
                        if b == True:
                            JSON_response(conn, { "error": False, "message": "Listener started successfully." })
                            return True
                        
                            #response_status = "200 OK"
                            #response_type = "application/json"
                            #response_body = json.dumps({ "error": False, "message": "Listener started successfully." })
                        else:
                            JSON_response(conn, { "error": True, "message": "Listener already running." })
                            return False
                        
                            #response_status = "500 Internal Server Error"
                            #response_type = "application/json"
                            #response_body = json.dumps({ "error": True, "message": "Listener already running." })
                
                    elif my_cmd == "audio_out_start":
                        
                        self._isAudioOut = True
                        JSON_response(conn, { "error": False, "message": "Pausing Listener during speech utterence." })
                        return True
                        #response_status = "200 OK"
                        #response_type = "application/json"
                        #response_body = json.dumps({ "error": False, "message": "Pausing Listener during speech utterence." })
                    
                    elif my_cmd == "audio_out_end":
                        
                        self._isAudioOut = False
                        JSON_response(conn, { "error": False, "message": "Engaging Listener after speech utterence." })
                        return True
                        #response_status = "200 OK"
                        #response_type = "application/json"
                        #response_body = json.dumps({ "error": False, "message": "Engaging Listener after speech utterence." })
                    
                    else:
                        JSON_response(conn, { "error": True, "message": "Invalid command" }, http_status_code=500, http_status_message="Internal Server Error")
                        return False
                        #response_status = "500 Internal Server Error"
                        #response_type = "application/json"
                        #response_body = json.dumps({ "error": True, "message": "Invalid command" })
                else:
                    JSON_response(conn, { "error": True, "message": "Invalid command" }, http_status_code=500, http_status_message="Internal Server Error")
                    return False
                    #response_status = "500 Internal Server Error"
                    #response_type = "application/json"
                    #response_body = json.dumps({ "error": True, "message": "Invalid command" })
            
            if (len(path) == 5 and path == "/data") or (len(path) > 5 and path[:6] == "/data/"):
                
                if "type" in payload:
                    my_cmd = str(payload["type"]).lower()
                    
                    if my_cmd == "history":
                        JSON_response(conn, { "error": False, "message": "Listener Data History.", "data": self._input })
                        return True
            #else:
                #JSON_response(conn, { "error": True, "message": "Invalid request" }, http_status_code=404, http_status_message="Not Found")
                #response_status = "404 Not Found"
                #response_type = "application/json"
                #response_body = json.dumps({ "error": True, "message": "Invalid request" })
                
            
            JSON_response(conn, { "error": True, "message": "Invalid request" }, http_status_code=404, http_status_message="Not Found")
            return False
    
        except:
            return False
    
        #response_text = "HTTP/1.1 "+response_status+"\nDate: "+time.strftime("%a, %d %b %Y %H:%M:%S %Z")+"\nContent-Type: "+response_type+"\nContent-Length: "+str(len(response_body)) + "\n\n"
        #conn.send(response_text.encode())
        #conn.send(response_body.encode())

            
        #conn.shutdown(socket.SHUT_RDWR)
        #conn.close()
                
    @threaded    
    def _processAudio(self, text):
        
        if self.isOffline == False:
        
            if self.use_http == True:
                url = "http://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/data"
            else:
                url = "https://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/data"
                
            mydata = { "type": "AUDIO_INPUT", "data": text }
            
            x_ret = JSON_request(url, mydata)
            if x_ret["error"] == False:
                return True
            else:
                try:
                    msg = json.loads(x_ret["message"])
                    logging.debug(self._name + " - Audio processing error - " + str(msg["message"]))
                except:
                    logging.debug(self._name + " - Audio processing error - " + str(x_ret["message"]))
                return False
            
        return True
    
    @threaded
    def _read_from_mic(self):
        """Opens audio device for listening and processing speech to text"""
 
        threadPool = []                 # Stores local thread pointer for processing incoming speech as a 
                                        # separate thread in order to avoid blocking the listening queue

        buffer_queue = queue.Queue()    # Buffer queue for incoming frames of audio
        self._Listener_running = True   # Reset to True to insure we can successfully start

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

        # Set up C lib error handler for Alsa programs to trap errors from Alsa spin up
        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)

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
        while self._Listener_running == True:

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
                        for f in ring_buffer:
                            stream_context.feedAudioContent(np.frombuffer(f[0], np.int16))

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
                        if self._Listener_running == True:
                            
                            # We'll only process if the text if there is a real value AND we're not already processing something.
                            # We don't block the processing of incoming audio though, we just ignore it if we're processing data.
                            if text.strip() != "":

                                logging.info(self._name + " - Heard: " + text)
                                
                                # Save the input to the history
                                self._input.append(text)

                                # If we have more than 10 entries then throw away the oldest entry.
                                if (len(self._input) > 10):
                                    self._input.pop(0)

                                # Start a thread for processing the parsed text.
                                # Using a thread here to prevent blocking of listening.
                                
                                t = self._processAudio(text)
                                threadPool.append(t)
                                
                                # Manage thread pool
                                i = len(threadPool) - 1
                                while i >= 0:
                                    if (threadPool[i].isAlive() == False):
                                        threadPool.pop(i)
                                    i = i - 1
                                
                                threadPool.append(t)
                                
                            stream_context = self._model.createStream() # Create a fresh new context

                        ring_buffer.clear() # Clear the ring buffer as we've crossed the threshold again

        logging.debug(self._name + " - Stopping streams")        
        stream.stop_stream()                          # Stop audio device stream
        stream.close()                                # Close audio device stream
        logging.debug(self._name + " - Streams stopped")
    
    def startListening(self):
        
        if (self._Listener_thread is None or self._Listener_thread.isAlive() == False):
            self._Listener_thread = self._read_from_mic()
            return True
        else:
            logging.debug(self._name + " - Listener already running")
            return False
        
    def stopListening(self):
        
        self._Listener_running = False
        
        if (self._Listener_thread is not None and self._Listener_thread.isAlive()):
            self._Listener_thread.join()
            self._Listener = None
            
        return True 
    
    def run(self):
        
        try:
            
            self._TCPServer_thread = self._ThreadedTCPServer()

            if self.DISABLE_ON_START == False:
                self.startListening()
            
            if (self._TCPServer_thread is not None and self._TCPServer_thread.isAlive()):
                self._TCPServer_thread.join()
                
            if (self._Listener_thread is not None and self._Listener_thread.isAlive()):
                self._Listener_thread.join()
            
        except KeyboardInterrupt:
            self.stop()
        
    def stop(self):
        
        self._Listener_running = False
        
        if (self._Listener_thread is not None and self._Listener_thread.isAlive()):
            self._Listener_thread.join()
        
        if self._audio_device is not None:
            self._audio_device.terminate()
            self._audio_device = None
        
        super().stop()