'''
Project Karen: Synthetic Human
Created on Jul 12, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: Watcher Daemon

'''

import os, logging, time

import cv2 
from PIL import Image
import numpy as np

from .KHTTP import TCPServer, KHTTPRequest, JSON_request, JSON_response
from .KShared import threaded

class Watcher(TCPServer):
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)

        # Daemon default name (make sure to always set this on inheritance!)
        self._name = "WATCHER"
        
        # TCP Command Interface
        self.tcp_port = kwargs["port"]            # TCP Port for listener.
        self.hostname = kwargs["ip"]     # TCP Hostname
        self.use_http = kwargs["use_http"]
        self.keyfile=kwargs["ssl_keyfile"]
        self.certfile=kwargs["ssl_certfile"]
        
        self.brain_ip=kwargs["brain_ip"]
        self.brain_port=kwargs["brain_port"]
        self.auto_register = True
        
        self.input_folder = kwargs["input_folder"]
        
        # Video Device Index
        self.VIDEO_DEVICE_ID = kwargs["device"]

        # Model for object recognition (e.g. Faces)
        self.MODEL_FILE = kwargs["model"]
        if self.MODEL_FILE is None:
            self.MODEL_FILE = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        
        # Model for recognizing the objects that were detected.
        # e.g. Who's face it is that we're looking at.
        self.TRAINED_FILE = kwargs["trained"]
        if self.TRAINED_FILE is None or self.TRAINED_FILE.strip() == "":
            import tempfile
            self.TRAINED_FILE = os.path.join(tempfile.gettempdir(), "karen", "faces.yml")
            
        os.makedirs(os.path.dirname(self.TRAINED_FILE), exist_ok=True)
        
        # Watcher FPS determines the number of frames per second that we
        # want to process for incoming objects.  Since this is video
        # the FPS can be as high as the device/hardware supports
        # but in reality our view of the world doesn't need to
        # process every frame to know what we're seeing.
        
        # I'd recommend keeping  this around 1 to 2 frames per second at a max.
        
        if (kwargs["fps"] is None):
            self.FPS = float(1) # Default to 1 frame per second
        else:
            self.FPS = float(kwargs["fps"]) # Set based on input
            
        # If the video device is mounted incorrectly it may need to be rotated.
        # This is especially true in some of the Raspberry Pi applications.
        # Options are:
        #    90 ... to rotate 90 degrees clockwise
        #    -90 ... to rotate 90 degrees counterclockwise
        #    180 ... to essentially flip the image (rotate 180 degrees)
        self.rotate = kwargs["rotate"]
        
        self._video_device = None       # Video Device Object (so we don't keep recapturing when not needed)
        self.DISABLE_ON_START = False   # Disable video capture on initialization
        self._KILL_SWITCH = True        # Kill Switch that breaks the video stream when shutting down
        self._threadWatching = None     # Thread for capturing video frames
        self._OFFLINE = False           # Indicates if the brain is offline (unable to connect)
        self._PAUSE = False             # Pause sending updates of faces
        
        self._dataset = None            # Our trained data set of faces (who belongs to which face)
        
        # The face detection model (to identify all faces (known/unknown) in a video framez
        # https://github.com/opencv/opencv/tree/master/data
        self._model = cv2.CascadeClassifier(self.MODEL_FILE);
        
        self._threadPool_watcher = []

        
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
            
                elif my_cmd == "start_watcher":
                    ret_val = self._startWatching()
                    if (ret_val):
                        JSON_response(conn, { "error": False, "message": "Watcher started." })
                    else:
                        JSON_response(conn, { "error": True, "message": "Failed to start watcher.  May already be running." })
                        return False

                    return True
                
                elif my_cmd == "stop_watcher":
                    ret_val = self._stopWatching()
                    if (ret_val):
                        JSON_response(conn, { "error": False, "message": "Watcher stopped." })
                    else:
                        JSON_response(conn, { "error": True, "message": "Failed to stop watcher." })
                        return False

                    return True
                
                elif my_cmd == "train":
                    ret_val = self.train()
                    if (ret_val):
                        JSON_response(conn, { "error": False, "message": "Training complete." })
                    else:
                        JSON_response(conn, { "error": True, "message": "Training failed." })
                        return False
                    
                    return True

                else:
                    JSON_response(conn, { "error": True, "message": "Invalid command." }, http_status_code=500, http_status_message="Internal Server Error")
                    return False

        
        JSON_response(conn, { "error": True, "message": "Invalid request" }, http_status_code=404, http_status_message="Not Found")
        return False
    
    @threaded
    def _read_from_camera(self):
        """Primary goodness of the Wather Daemon.  
        
        Reads and processes the video frames through our model
        and recognizer."""
        
        # Reset our kill switch so that we have a nice clean start.
        self._KILL_SWITCH = False
        
        # Initialize the recognizer for determining the specifics behind the object detected.  
        # (e.g. Who's face it is that we detected)
        # Putting this here so we can restart the watcher to refresh the trained data set
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(self.TRAINED_FILE)  # Load our trained data set

        # Run until killed        
        while self._KILL_SWITCH == False:
            
            # Get a frame from the video device (yes, just one frame)
            ret, im = self._video_device.read()
            if ret:
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
                    self._PAUSE = False # Used to send the latest frame, even if no people are present
                
                # Send the list of people in the frame to the brain.
                # We do this on a separate thread to avoid blocking the image capture process.
                # Technically we could have offloaded the entire recognizer process to a separate 
                # thread so may need to consider doing that in the future.
                if (len(people) > 0) or self._PAUSE == False:
                    # We only send data to the brain when we have something to send.
                    t = self.sendWatcherData(people)
                    self._threadPool_watcher.append(t)
                    
                    i = len(self._threadPool_watcher) - 1
                    while i >= 0:
                        try:
                            # Simple check to see if the thread is alive.
                            if self._threadPool_watcher[i].isAlive() == False:
                                # If thread is dead then we don't need it any more.
                                self._threadPool_watcher.pop(i)
                        except:
                            self._threadPool_watcher.pop(i)
                            
                        i = i - 1
                    
                    self._PAUSE = True # Set to pause unless I have people.
                    
                if (len(people) > 0):
                    self._PAUSE = False # Need to sort out the logic b/c we shouldn't have to count the array again.
                
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
        
        # Let's make sure we have a trained data set to work with before we fire up the watcher.
        if self.TRAINED_FILE is None or os.path.exists(self.TRAINED_FILE) == False:
            logging.error(self._name + " - Trained file does not exist.  Please try training with --watcher-exec-train")
            self.stop()
            return False
        
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

        # Lastly, let's just doublecheck that any open threads are really finished.
        for x in self._threadPool_watcher:
            try:
                if x.isAlive():
                    x.join()
            except:
                pass
        
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
        
        # Lastly, let's make sure anything left running is actually finished.
        for x in self._threadPool_watcher:
            try:
                if x.isAlive():
                    return True
            except:
                pass

        # At this point it looks like everything is dead/not running so we can assume we're not alive.
        return False
    
    def run(self):
        """Kicks off the main thread runtime for the Daemon.
        
        Will continue running until watcher is stopped or thread fails."""
        if self.TRAINED_FILE is None or os.path.exists(self.TRAINED_FILE) == False:
            if self.input_folder is not None and os.path.exists(self.input_folder) == True:
                logging.info(self._name + " - Trained file not found.  Attempting to train now.")
                self.train()
            else:
                logging.error(self._name + " - Startup failed:  Trained file not found.  Did you already train?")
                return False
        
        # If we were were not disabled on start then we need to start listening.
        if self.DISABLE_ON_START == False:
            ret_val = self._startWatching() # Starts its own thread
            
            if ret_val == False:
                return False
            
        
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

    @threaded
    def sendWatcherData(self, data):
        """Simple thread used to send captured data to the brain"""
        
        try:
            
            if self.use_http == True:
                url = "http://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/data"
            else:
                url = "https://" + str(self.brain_ip) + ":" + str(self.brain_port) + "/data"
            
            # Attempt sending the data to the brain
            x_ret = JSON_request(url, { "type": "WATCHER_DATA", "data": data })

            self._OFFLINE = False       # If we were offline then now we know we aren't 
                                        # as the send command must be successful to reach 
                                        # this point.
            
            try:
                # Check if we had an error on the brain (although we don't really care so much).
                if (x_ret["error"] == True):
                    logging.warning(self._name + " - An error occurred")
            except Exception as e:
                # Hmm... something bad happened here.
                logging.error(self._name + " - Error: " + str(e))
                
        except:

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
        if self.input_folder is None or os.path.exists(self.input_folder) == False:
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
        imagePaths = [os.path.join(self.input_folder,f) for f in os.listdir(self.input_folder)]
        
        # Set up a few arrays for capturing data
        faceSamples=[]
        ids = []

        model = cv2.CascadeClassifier(self.MODEL_FILE);

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
                faces = model.detectMultiScale(img_numpy)
            
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
    
