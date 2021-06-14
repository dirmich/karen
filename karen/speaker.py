'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Speaker function translating text to speech and outputting to speakers
'''

import os, logging
from .shared import threaded
import tempfile

class Speaker():
    """
    Speaker device to convert any text to speech send to the audio output device.
    """
    
    def __init__(
            self, 
            callback=None):             # Callback is a function that accepts ONE positional argument which will contain the text identified
        """
        Speaker Initialization

        Args:
            callback (function): Callback function for which to send any captured data.
        """

        # Local variable instantiation and initialization
        self.type = "SPEAKER"
        self.callback = callback
        self.logger = logging.getLogger("SPEAKER")
        
        self._isRunning = False
        
    @threaded
    def _doCallback(self, text):
        """
        Calls the specified callback as a thread to keep from blocking additional processing.

        Args:
            text (str):  Text to send to callback function
        
        Returns:
            (thread):  The thread on which the callback is created to be sent to avoid blocking calls.
        """

        try:
            if self.callback is not None:
                self.callback(text)
        except:
            pass
        
        return
    
    def say(self, text):
        """
        Sends text to the festival executable to be translated and sent to the audio device.
        
        Args:
            text (str):  The text to convert into speech.
            
        Returns:
            (bool): True on success else raises exception.
        """
        
        fd, say_file = tempfile.mkstemp()
            
        with open(say_file, 'w') as f:
            f.write(str(text)) 
            
        self.logger.info("SAYING " + str(text))
        os.system("festival --tts "+say_file )
        os.close(fd)
        
        return True
    
    def stop(self):
        """
        Stops the speaker.  Function provided for compatibility as speaker does not require a daemon.
        
        Returns:
            (bool):  True on success else will raise an exception.
        """
        
        return True
        
    def start(self, useThreads=True):
        """
        Starts the speaker.  Function provided for compatibility as speaker does not require a daemon.

        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
        
        Returns:
            (bool):  True on success else will raise an exception.
        """
        return True
    
    def wait(self, seconds=0):
        """
        Waits for any active speakders to complete before closing.  Provided for compatibility as speaker does not requrie a daemon.
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        return True
