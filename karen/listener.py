import os, sys, logging
import numpy as np
import pyaudio, queue, webrtcvad, collections
import deepspeech
from ctypes import CFUNCTYPE, cdll, c_char_p, c_int
import time

from .shared import threaded

def py_error_handler(filename, line, function, err, fmt):
    """
    Error handler to translate non-critical errors to logging messages.
    
    Args:
        filename (str): Output file name or device (/dev/null).
        line (int): Line number of error
        function (str): Function containing
        err (Exception): Exception raised for error
        fmt (str): Format of log output
    """

    # Convert the parameters to strings for logging calls
    fmt = fmt.decode("utf-8")
    filename = filename.decode("utf-8")
    fnc = function.decode('utf-8')
    
    # Setting up a logger so you can turn these errors off if so desired.
    logger = logging.getLogger("CTYPES")

    if (fmt.count("%s") == 1 and fmt.count("%i") == 1):
        logger.debug(fmt % (fnc, line))
    elif (fmt.count("%s") == 1):
        logger.debug(fmt % (fnc))
    elif (fmt.count("%s") == 2):
        logger.debug(fmt % (fnc, str(err)))
    else:
        logger.debug(fmt)
    return

class SilenceStream():
    """
    Hides C library messages by redirecting to log file
    """
    
    def __init__(self, stream, log_file=None, file_mode='a'):
        """
        Redirect stream to log file
        
        Args:
            stream (stream): Inbound stream containing errors to hide
            log_file (str): File name or device name for error log
            file_mode (str): Mode to open log_file
        """
        
        self.fd_to_silence = stream.fileno() # Store the stream we're referening
        self.log_file = log_file # Store the log file to redirect to
        self.file_mode = file_mode # Append vs. Writex

    def __enter__(self):
        """
        Starts the stream redirection to the log file
        """

        if (self.log_file is None): 
            return # No log file means we can skip this and let output flow as normal.
        
        self.stored_dup = os.dup(self.fd_to_silence) # Store the original pointer for the stream
        self.devnull = open(self.log_file, self.file_mode) # Get a pointer for the new target
        os.dup2(self.devnull.fileno(), self.fd_to_silence) # Redirect to the new pointer

    def __exit__(self, exc_type, exc_value, tb):
        """
        Restore stream back to its original state before the silencer was called.
        
        Args:
            exc_type (obj): Execution type. Not used.
            exc_value (obj): Execution value. Not used.
            tb (obj): Traceback. Not used.
        """

        if (self.log_file is None): 
            return  # No log file means we can skip this as nothing needs to change.
        
        os.dup2(self.stored_dup, self.fd_to_silence) # Restore the pointer to the original
        self.devnull = None # Cleanup
        self.stored_dup = None # Cleanup

class Listener():
    """
    Listener device to capture audio from microphone and convert any speech to text and send to callback method.
    """
    
    def __init__(
            self, 
            speechModel=None,           # Speech Model file.  Ideally this could be searched for in a default location
            speechScorer=None,          # Scorer file.  Okay for this to be None as scorer file is not required
            audioChannels=1,            # VAD requires this to be 1 channel
            audioSampleRate=16000,      # VAD requires this to be 16000
            vadAggressiveness=1,        # VAD accepts 1 thru 3
            speechRatio=0.75,           # Must be between 0 and 1 as a decimal
            speechBufferSize=50,        # Buffer size for speech frames
            speechBufferPadding=350,    # Padding, in milliseconds, of speech frames
            audioDeviceIndex=None,
            callback=None):             # Callback is a function that accepts ONE positional argument which will contain the text identified
        """
        Listener Initialization

        Args:
            speechModel (str):  Path and filename of Deepspeech Speech Model file.  If not set then listener will do a basic seach for the PBMM or TFLite file.
            speechScorer (str):  Path and filename of Deepspeech Scorer file.  Okay for this to be None as scorer file is not required.
            audioChannels (int):  Audio channels for audio source.  VAD requires this to be 1 channel.
            audioSampleRate (int): Audio sample rate of audio source.  VAD requires this to be 16000.
            vadAggressiveness (int): Voice Activity Detection (VAD) aggressiveness for filtering noise.  Accepts 1 thru 3.
            speechRatio (float): Must be between 0 and 1 as a decimal
            speechBufferSize (int): Buffer size for speech frames
            speechBufferPadding (int): Padding, in milliseconds, of speech frames
            audioDeviceIndex (int): Listening device index number.  If not set then will use default audio capture device.
            callback (function): Callback function for which to send capture text    
        """

        # Local variable instantiation and initialization
        self.type = "LISTENER"
        self.callback = callback
        self.logger = logging.getLogger("LISTENER")

        self.speechModel=speechModel
        self.speechScorer=speechScorer                  
        self.audioChannels=audioChannels                
        self.audioSampleRate=audioSampleRate            
        self.vadAggressiveness=vadAggressiveness        
        self.speechRatio=speechRatio                    
        self.speechBufferSize=speechBufferSize          
        self.speechBufferPadding=speechBufferPadding
        self.audioDeviceIndex=audioDeviceIndex

        if self.speechModel is None:
            # Search for speech model?
            self.logger.info("Speech model not specified.  Attempting to use defaults.")
            local_path = os.path.join(os.path.dirname(__file__), "..", "models", "speech")
            files = os.listdir(local_path)
            files = sorted(files, reverse=True) # Very poor attempt to get the latest version of the model if multiple exist.
            bFoundPBMM=False 
            bFoundTFLITE=False
            for file in files:
                if not bFoundPBMM:
                    if file.startswith("deepspeech") and file.endswith("models.pbmm"):
                        self.speechModel=os.path.abspath(os.path.join(local_path, file))
                        self.logger.debug("Using speech model from " + str(self.speechModel))
                        bFoundPBMM = True
                        
                if not bFoundPBMM and not bFoundTFLITE:
                    if file.startswith("deepspeech") and file.endswith("models.tflite"):
                        self.speechModel=os.path.abspath(os.path.join(local_path, file))
                        self.logger.debug("Using speech model from " + str(self.speechModel))
                        bFoundTFLITE = True

                if self.speechScorer is None:
                    if file.startswith("deepspeech") and file.endswith("models.scorer"):
                        self.speechScorer=os.path.abspath(os.path.join(local_path, file))
                        self.logger.debug("Using speech scorer from " + str(self.speechScorer))
        
            if bFoundPBMM and bFoundTFLITE:
                self.logger.warning("Found both PBMM and TFLite deepspeech models.")
                self.logger.warning("Defaulting to PBMM model which will not work with Raspberry Pi devices.")
                self.logger.warning("To use with RPi either delete the PBMM model or specify the TFLite model explicitly.")
                
        if self.speechModel is None:
            #FIXME: Should we try to download the models if they don't exist?
            raise Exception("Invalid speech model.  Unable to start listener.")
        
        self.stream = None
        self.thread = None
        self._isRunning = False 
        self._isAudioOut = False 
        
    @threaded
    def _doCallback(self, text):
        """
        Calls the specified callback as a thread to keep from blocking audio device listening

        Args:
            text (str):  Text to send to callback function
        
        Returns:
            (thread):  The thread on which the callback is created to be sent to avoid blocking calls.
        """

        try:
            if self.callback is not None:
                self.callback("AUDIO_INPUT", text)
        except:
            pass
        
        return

    @threaded
    def _readFromMic(self):
        """
        Opens audio device for listening and processing speech to text
        
        Returns:
            (thread):  The thread created for the listener while listening for incoming speech.
        """
    
        buffer_queue = queue.Queue()    # Buffer queue for incoming frames of audio
        self._isRunning = True   # Reset to True to insure we can successfully start
    
        def proxy_callback(in_data, frame_count, time_info, status):
            """Callback for the audio capture which adds the incoming audio frames to the buffer queue"""
            
            # Save captured frames to buffer
            buffer_queue.put(in_data)
            
            # Tell the caller that it can continue capturing frames
            return (None, pyaudio.paContinue)
    
        # Using a collections queue to enable fast response to processing items.
        # The collections class is simply faster at handling this data than a simple dict or array.
        # The size of the buffer is the length of the padding and thereby those chunks of audio.
        ring_buffer = collections.deque(maxlen=self.speechBufferPadding // (1000 * int(self.audioSampleRate / float(self.speechBufferSize)) // self.audioSampleRate))
    
        # Set up C lib error handler for Alsa programs to trap errors from Alsa spin up
        #ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        #c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        #asound = cdll.LoadLibrary('libasound.so')
        #asound.snd_lib_error_set_handler(c_error_handler)
        with SilenceStream(sys.stderr, log_file="/dev/null"):
            _model = deepspeech.Model(self.speechModel)
            if self.speechScorer is not None:
                _model.enableExternalScorer(self.speechScorer)
            
        _vad = webrtcvad.Vad(self.vadAggressiveness)
        
        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        
        _audio_device = pyaudio.PyAudio()
        
        # Open a stream on the audio device for reading frames
        self.stream = _audio_device.open(format=pyaudio.paInt16,
            channels=self.audioChannels,
            rate=self.audioSampleRate,
            input=True,
            frames_per_buffer=int(self.audioSampleRate / float(self.speechBufferSize)),
            input_device_index=self.audioDeviceIndex,
            stream_callback=proxy_callback)
        
        self.stream.start_stream()                               # Open audio device stream
        
        stream_context = _model.createStream()         # Context of audio frames is used to 
                                                            # better identify the spoken words.
        
        triggered = False                                   # Used to flag whether we are above
                                                            # or below the ratio threshold set
                                                            # for speech frames to total frames
        
        self.logger.info("Started")
        
        # We will loop looking for incoming audio until the KILL_SWITCH is set to True
        while self._isRunning == True:
    
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
                is_speech = _vad.is_speech(frame, self.audioSampleRate)
            
                # Trigger is set for first frame that contains speech and remains triggered until 
                # we fall below the allowed ratio of speech frames to total frames
    
                if not triggered:
    
                    # Save the frame to the buffer along with an indication of if it is speech (or not)
                    ring_buffer.append((frame, is_speech))
    
                    # Get the number of frames with speech in them
                    num_voiced = len([f for f, speech in ring_buffer if speech])
    
                    # Compare frames with speech to the expected number of frames with speech
                    if num_voiced > self.speechRatio * ring_buffer.maxlen:
                        
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
                    if num_unvoiced > self.speechRatio * ring_buffer.maxlen:
                        
                        # We have fallen below the threshold for speech per frame ratio
                        triggered = False
                        
                        # Let's see if we heard anything that can be translated to words.
                        # This is the invocation of the deepspeech's primary STT logic.
                        # Note that this is outside the kill_switch block just to insure that all the
                        # buffers are cleaned and closed properly.  (Arguably this is not needed if killed)
                        text = str(stream_context.finishStream())
    
                        # We've completed the hard part.  Now let's just clean up.
                        if self._isRunning == True:
                            
                            # We'll only process if the text if there is a real value AND we're not already processing something.
                            # We don't block the processing of incoming audio though, we just ignore it if we're processing data.
                            if text.strip() != "":
    
                                self.logger.info("HEARD " + text)
                                self._doCallback(text)
                                
                            stream_context = _model.createStream() # Create a fresh new context
    
                        ring_buffer.clear() # Clear the ring buffer as we've crossed the threshold again
    
        self.logger.debug("Stopping streams")        
        self.stream.stop_stream()                          # Stop audio device stream
        self.stream.close()                                # Close audio device stream
        self.logger.debug("Streams stopped")
    
    def stop(self):
        """
        Stops the listener and any active audio streams
        
        Returns:
            (bool):  True on success else will raise an exception.
        """

        if not self._isRunning:
            return True 

        self._isRunning = False
        if self.thread is not None:
            if not self.wait():
                return False 
            
        self.logger.info("Stopped")
        return True
        
    def start(self, useThreads=True):
        """
        Starts the listener to listen to the default audio device

        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
        
        Returns:
            (bool):  True on success else will raise an exception.
        """
        if self._isRunning:
            return True 
        
        self.thread = self._readFromMic()
        if not useThreads:
            self.wait()
            
        return True
    
    def wait(self, seconds=0):
        """
        Waits for any active listeners to complete before closing
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        if not self._isRunning:
            return True 
        
        if seconds > 0:
            if self.thread is not None:
                time.sleep(seconds)
                self.stop()
        
        else:
            if self.thread is not None:
                self.thread.join()
            
        return True

    