import os, logging
import time
from .shared import threaded
import tempfile 
import json 
import cv2 
from PIL import Image
import numpy as np

class Watcher():
    """
    Watcher device to capture and process inbound video stream for objects and faces.
    """
    
    def __init__(
            self, 
            classifierFile=None,
            recognizerFile=None,
            namesFile=None,
            trainingSourceFolder=None,
            videoDeviceIndex=0,
            framesPerSecond=1.0,
            orientation=0,
            callback=None):             # Callback is a function that accepts ONE positional argument which will contain the text identified
        """
        Watcher Initialization

        Args:
            classifierFile (str):  Classifier file such as haarcascades to identify generic objects.
            recognizerFile (str): Trained file to be used to identify specific objects. (optional)
            namesFile (str):  File with friendly names tied to recognizer trained data set. (optional)
            trainingSourceFolder (str):  The source directory that contains all the images to use for building a new recognizerFile.
            videoDeviceIndex (int): Video Device identifier. (optional)
            orientation (int): Device orientation which can be 0, 90, 180, or 270.  (optional)
            videoDeviceIndex (int): Video device index number.  If not set then will use default video capture device.
            callback (function): Callback function for which to send any captured data.
        """

        # Local variable instantiation and initialization
        self.type = "WATCHER"
        self.callback = callback
        self.logger = logging.getLogger("WATCHER")
        
        self.classifierFile = classifierFile if classifierFile is not None else os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "models", "watcher", "haarcascade_frontalface_default.xml"))
        self.recognizerFile = recognizerFile if recognizerFile is not None else os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "models", "watcher", "recognizer.yml"))
        self.namesFile = namesFile if namesFile is not None else os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "models", "watcher", "names.json"))

        self.trainingSourceFolder = trainingSourceFolder
        self.videoDeviceIndex = videoDeviceIndex if videoDeviceIndex is not None else 0
        self.framesPerSecond = float(framesPerSecond) if framesPerSecond is not None else 1.0
        
        self.orientation = None
        if orientation == 90:
            self.orientation = cv2.ROTATE_90_CLOCKWISE
        elif orientation == 180:
            self.orientation = cv2.ROTATE_180
        elif orientation == 270 or orientation == -90:
            self.orientation = cv2.ROTATE_90_COUNTERCLOCKWISE
        
        self.isRunning = False
        
    @threaded
    def _doCallback(self, inData):
        """
        Calls the specified callback as a thread to keep from blocking additional processing.

        Args:
            text (str):  Text to send to callback function
        
        Returns:
            (thread):  The thread on which the callback is created to be sent to avoid blocking calls.
        """

        try:
            if self.callback is not None:
                self.logger.debug(str(inData))
                self.callback("IMAGE_INPUT", inData)
        except:
            pass
        
        return
    
    @threaded
    def _readFromCamera(self):
        """
        Opens video device for capture and processing for inputs
        
        Returns:
            (thread):  The thread created for the watcher while capturing incoming video.
        """
        self.isRunning = True
        
        if self.classifierFile is None or not os.path.isfile(self.classifierFile):
            self.logger.error("Invalid classifier file specified. Unable to start Watcher.")
            self.classifierFile = None 
            self.isRunning = False
            return False
        
        classifier = cv2.CascadeClassifier(self.classifierFile)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        if self.recognizerFile is None or not os.path.isfile(self.recognizerFile):
            if self.classifierFile is not None and self.trainingSourceFolder is not None and os.path.isdir(self.trainingSourceFolder):
                self.logger.info("Recognizer file not found.  Will attempt to generate.")
                if not self.train():
                    self.logger.critical("Unable to start watcher due to failed recognizer build.")
                    self.isRunning = False
                    return False 
            else:
                self.logger.warning("Invalid recognizer file and no training source was provided. Named objects will not be detected.")
                recognizer = None
        else:
            recognizer.read(self.recognizerFile)
            
        names = { }
        if self.namesFile is not None and os.path.isfile(self.namesFile):
            with open(self.namesFile, 'r') as fp:
                obj = json.load(fp)
            
            if isinstance(obj,list):
                for item in obj:
                    if "id" in item and "name" in item:
                        names[item["id"]] = item["name"]
            
        isPaused = False 
        
        videoDevice = cv2.VideoCapture(self.videoDeviceIndex)
        threadPool = []
        
        while self.isRunning:
            ret, im = videoDevice.read()
            
            if ret:
                # See if we need to rotate it and do so if required
                if self.orientation is not None:
                    im = cv2.rotate(im, self.orientation)
                
                # Convert image to grayscale.  
                # Some folks believe this improves identification, but your mileage may vary.
                gray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
                
                # Detect faces (not the who... just if I see a face).
                # Returns an array for each face it sees in the frame.
                faces = classifier.detectMultiScale(gray, 1.2,5)
                
                # Since we care about all the faces we'll store them after they are processed in an array
                people = []
                
                # Iterate through the faces for identification.
                for (x,y,w,h) in faces:
    
                    # Pull the ID and Distance from the recognizer based on the face in the image
                    # Remember that "gray" is our image now so this is literally cutting out the face
                    # at the coordinates provided and attempting to predict the person it is seeing.
                    
                    if recognizer is None:
                        Id = [0,0]
                    else:
                        Id = recognizer.predict(gray[y:y+h,x:x+w])

                    # Let's build a JSON array of the person based on what we've learned so far.
                    person = {
                            "id":Id[0],
                            "name": names[Id[0]] if Id[0] in names else "",
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
                    isPaused = False # Used to send the latest frame, even if no people are present
                
                # Send the list of people in the frame to the brain.
                # We do this on a separate thread to avoid blocking the image capture process.
                # Technically we could have offloaded the entire recognizer process to a separate 
                # thread so may need to consider doing that in the future.
                if (len(people) > 0) or isPaused == False:
                    # We only send data to the brain when we have something to send.
                    t = self._doCallback(people) 
                    
                    i = len(threadPool) - 1
                    while i >= 0:
                        try:
                            if threadPool[i].isAlive() == False:
                                threadPool[i].join()
                                threadPool.pop(i)
                        except:
                            pass
                            
                        i = i - 1
                    
                    threadPool.append(t)
                    isPaused = True # Set to pause unless I have people.
                    
                if (len(people) > 0):
                    isPaused = False # Need to sort out the logic b/c we shouldn't have to count the array again.
                
                # Here we are trying to read only 1 frame per the defined FPS setting (default to 1 per sec).
                # Standard NTSC is 30+ frames per second so this should significantly
                # reduce the load on the server.  It will also cut down on chatter to
                # the brain.
                    
                t = time.time()
                while time.time() < (t+(1 // float(self.framesPerSecond))):
                    # In order to process frames without delay we have to "grab" the data in
                    # between our frame captures.  Seems strange, but it's needed.
                    videoDevice.grab()
        
        videoDevice.release()
        for item in threadPool:
            item.join()
    
    def train(self, trainingSourceFolder=None):
        """
        Retrains the face recognition based on images in the supplied folder
        
        Args:
            trainingSourceFolder (str): The source directory that contains all the images to use for building a new recognizerFile.  Will use the configuration value if the input value is left empty. (optional)
            
        Returns:
            (bool): True on success or False on failure
            
        """
        if trainingSourceFolder is not None:
            self.trainingSourceFolder = trainingSourceFolder
        
        if self.trainingSourceFolder is None or not os.path.isdir(self.trainingSourceFolder):
            self.logger.error("Invalid training source folder specified.  Unable to retrain recognizer file.")
            return False
        
        self.logger.debug("Using " + str(self.trainingSourceFolder) + " for building recognizer file.")
        
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        classifier = cv2.CascadeClassifier(self.classifierFile);
        
        samples = []
        ids = []
        names = []

        namePaths = sorted([f.path for f in os.scandir(self.trainingSourceFolder) if f.is_dir()])
        for i, entry in enumerate(namePaths):
            names.append({ "id": (i+1), "name": os.path.basename(entry) })
            self.logger.info("Processing " + os.path.basename(entry) + " directory")
            imagePaths = sorted([f.path for f in os.scandir(entry) if f.is_file()])
            # Loop through input images in the folder supplied.
            for imagePath in imagePaths:
                
                try:
                    # Open the image as a resource
                    PIL_img = Image.open(imagePath).convert('L')
                
                    # Convert to Numpy Array
                    img_numpy = np.array(PIL_img,'uint8')
                
                    # At this point we should be okay to proceed with the image supplied.
                    self.logger.debug("Processing " + imagePath)
                
                    # Let's pull out the faces from the image (may be more than one!)
                    faces = classifier.detectMultiScale(img_numpy)
            
                    # Loop through faces object for detection ... and there should only be 1. 
                    for (x,y,w,h) in faces:
                    
                        # Let's save the results of what we've found so far.
                    
                        # Yes, we are cutting out the face from the image and storing in an array.
                        samples.append(img_numpy[y:y+h,x:x+w]) 
                    
                        # Ids go in the ID array.
                        ids.append(i+1)
                except:
                    self.logger.error("Failed to process: " + imagePath)
                    raise

        # Okay, we should be done collecting faces.
        self.logger.info("Identified " + str(len(samples)) + " sample images")
        
        # This is where the real work happens... let's create the training data based on the faces collected.
        recognizer.train(samples, np.array(ids))

        # And now for the final results and saving them to a file.
        self.logger.debug("Writing data to " + self.recognizerFile)
        recognizer.save(self.recognizerFile)
        
        self.logger.debug("Writing data to " + self.namesFile)
        with open(self.namesFile, 'w') as fp:
            json.dump(names, fp)
        
        self.logger.info("Training algorithm completed.")
        
        return True
    
    def stop(self):
        """
        Stops the watcher.  
        
        Returns:
            (bool):  True on success else will raise an exception.
        """

        if not self.isRunning:
            return True 

        self.isRunning = False
        if self.thread is not None:
            self.thread.join()
            
        self.logger.info("Stopped")
        return True
        
    def start(self, useThreads=True):
        """
        Starts the watcher.

        Args:
            useThreads (bool):  Indicates if the brain should be started on a new thread.
        
        Returns:
            (bool):  True on success else will raise an exception.
        """
        if self.isRunning:
            return True 
        
        self.thread = self._readFromCamera()
        if not useThreads:
            self.wait()
            
        return True
    
    def wait(self, seconds=0):
        """
        Waits for any active watchers to complete before closing.
        
        Args:
            seconds (int):  Number of seconds to wait before calling the "stop()" function
            
        Returns:
            (bool):  True on success else will raise an exception.
        """
        if not self.isRunning:
            return True 
        
        if seconds > 0:
            if self.thread is not None:
                time.sleep(seconds)
                self.stop()
        
        else:
            if self.thread is not None:
                self.thread.join()
            
        return True
