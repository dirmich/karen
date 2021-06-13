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
    
    def __init__(
            self, 
            callback=None):             # Callback is a function that accepts ONE positional argument which will contain the text identified

        # Local variable instantiation and initialization
        self.type = "SPEAKER"
        self.callback = callback
        self.logger = logging.getLogger("SPEAKER")
        
        self._isRunning = False
        
    @threaded
    def _doCallback(self, text):
        """Calls the specified callback as a thread to keep from blocking audio device listening"""

        try:
            if self.callback is not None:
                self.callback(text)
        except:
            pass
        
        return
    
    def say(self, text):
        fd, say_file = tempfile.mkstemp()
            
        with open(say_file, 'w') as f:
            f.write(str(text)) 
            
        self.logger.info("SAYING " + str(text))
        os.system("festival --tts "+say_file )
        os.close(fd)
    
    def stop(self):
        """Stops the speaker"""
        return True
        
    def start(self, useThreads=True):
        """Starts the speaker"""
        return True
    
    def wait(self, seconds=0):
        """Waits for any active speakers to complete before closing"""
        return True
