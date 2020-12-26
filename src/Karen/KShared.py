'''
Project Karen: Synthetic Human
Created on July 12, 2020

@author: lnxusr1
@license: MIT License
@summary: Shared Functions

'''
import os, time, logging, threading

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
    
def py_error_handler(filename, line, function, err, fmt):
    """Used as the handler for the trapped C module errors"""

    # Convert the parameters to strings for logging calls
    fmt = fmt.decode("utf-8")
    filename = filename.decode("utf-8")
    fnc = function.decode('utf-8')

    # Poor attempt at formating the output of the trapped errors
    fmt = "CTYPES - " + fmt
        
    if (fmt.count("%s") == 1 and fmt.count("%i") == 1):
        logging.debug(fmt % (fnc, line))
    elif (fmt.count("%s") == 1):
        logging.debug(fmt % (fnc))
    elif (fmt.count("%s") == 2):
        logging.debug(fmt % (fnc, str(err)))
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

def threaded(fn):
    """Thread wrapper shortcut using @threaded prefix"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper

class People:
    def __init__(self, in_data=None):
        self.data = in_data
        if in_data is None:
            self.data = dict()
        
    def addPerson(self, in_person, force_add=False):

        if in_person.confidence > 65:
            in_person.idx = -1

        # reset
        rg = range(0,len(self.data))
        for z in rg:
            self.data[z]["focus"] = False
            self.data[z]["lastFrame"] = False 
        
        # Update if exists
        bAdd = True
        
        if force_add == False:
            rg = range(0,len(self.data))
            for z in rg:
                if self.data[z]["idx"] == in_person.idx:
                    self.data[z]["confidence"] = in_person.confidence
                    self.data[z]["last_seen"] = time.time()
                    self.data[z]["focus"] = False
                    self.data[z]["width"] = in_person.width 
                    self.data[z]["height"] = in_person.height
                    self.data[z]["x"] = in_person.x
                    self.data[z]["y"] = in_person.y
                    self.data[z]["lastFrame"] = True
                    bAdd = False

        if bAdd:
            in_person.last_seen = time.time()
            in_person.focus = False
            in_person.lastframe = True
            self.data.append(in_person.info())
        
        return True
    
    def removePerson(self, in_idx):
        rg = range(len(self.data),0,-1)
        for z in rg:
            if self.data[z-1]["idx"] == in_idx:
                self.data.pop(z-1)
                
        return True
    
    def info(self):

        # Set focus
        max_w = 0
        idx = -1
        rg = range(0,len(self.data))
        for z in rg:
            if self.data[z]["width"] > max_w and idx == -1:
                max_w = self.data[z]["width"]
                idx = z
                
        if idx > -1:
            self.data[idx]["focus"] = True

        return self.data
    
class Person:

    def __init__(self, idx=-1, confidence=0, last_seen=0, focus=False, order=1, width=-1, height=-1, x=-1, y=-1, lastFrame=False):
        self.idx = idx
        self.confidence = confidence
        self.last_seen = last_seen
        self.focus = focus
        self.order = order
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.lastFrame = lastFrame
        
    def load(self, arr):
        self.idx = arr["idx"]
        self.confidence = arr["confidence"]
        self.last_seen = arr["last_seen"]
        self.focus = arr["focus"]
        self.order = arr["order"]
        self.width = arr["width"]
        self.height = arr["height"]
        self.x = arr["x"]
        self.y = arr["y"]
        self.lastFrame = arr["lastFrame"]

    def info(self):
        return { "idx": self.idx, "confidence": self.confidence, "last_seen": self.last_seen, "focus": self.focus, "order": self.order, "width": self.width, "height": self.height, "x": self.x, "y": self.y, "lastFrame": self.lastFrame }

