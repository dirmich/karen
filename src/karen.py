"""Project Karen : Synthetic Human"""

import os, sys, logging
import klib.KDaemon as kd
import threading
import kconfig

def threaded(fn):
    """Thread wrapper shortcut using @threaded prefix"""

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper

class Karen:
    """Primary object for Karen.  This is used to manage all
    the components that are executing under the main thread
    for this process."""
    
    def __init__(self, **kwargs):
        """Initialize the shell objects for each of the main functions."""
        
        self._kwargs = kwargs
        
        self._brain = None
        self._watcher = None
        self._speaker = None
        self._listener = None
        
        self._brainThread = None
        self._watcherThread = None
        self._speakerThread = None
        self._listenerThread = None

    def run(self):
        """Monitor process to wait for any running Daemons to exist before completing.
        
        This function does not start the Daemon processes directly."""
        
        if self._listenerThread is not None:
            try:
                self._listenerThread.join()
            except (KeyboardInterrupt):
                logging.warning("Process aborted prematurely.  Attempting clean shutdown.")
                self.stop()

        if self._speakerThread is not None:
            try:
                self._speakerThread.join()
            except (KeyboardInterrupt):
                logging.warning("Process aborted prematurely.  Attempting clean shutdown.")
                self.stop()
        
        if self._watcherThread is not None:
            try:
                self._watcherThread.join()
            except (KeyboardInterrupt):
                logging.warning("Process aborted prematurely.  Attempting clean shutdown.")
                self.stop()
                
        if self._brainThread is not None:
            try:
                self._brainThread.join()
            except (KeyboardInterrupt):
                logging.warning("Process aborted prematurely.  Attempting clean shutdown.")
                self.stop()
    
    def startBrain(self, **kwargs):
        """Instantiates and Starts the Brain Daemon for Karen"""

        if kwargs == {}:
            kwargs = self._kwargs
            
        self._brain = kd.Brain(**kwargs)
        
        self._brainThread = threading.Thread(target=self._brain.run)
        self._brainThread.start()
    
    def startListener(self, **kwargs):
        """Instantiates and Starts the Listener Daemon for Karen"""
        
        if kwargs == {}:
            kwargs = self._kwargs
            
        self._listener = kd.Listener(**kwargs)
        
        self._listenerThread = threading.Thread(target=self._listener.run)
        self._listenerThread.start()

    def startSpeaker(self, **kwargs):
        """Instantiates and Starts the Speaker Daemon for Karen"""
        
        if kwargs == {}:
            kwargs = self._kwargs
            
        self._speaker = kd.Speaker(**kwargs)
        
        self._speakerThread = threading.Thread(target=self._speaker.run)
        self._speakerThread.start()

    def startWatcher(self, **kwargs):
        """Instantiates and Starts the Watcher Daemon for Karen"""
        
        if kwargs == {}:
            kwargs = self._kwargs
            
        self._watcher = kd.Watcher(**kwargs)

        self._watcherThread = threading.Thread(target=self._watcher.run)
        self._watcherThread.start()
        
    def stop(self):
        """Stops all running Daemons contained in this runtime instance"""
        
        self.stopListener()
        self.stopWatcher()
        self.stopSpeaker()
        self.stopBrain()
        
    def stopBrain(self):
        """Stop the Brain instance's daemon"""
        
        if (self._brain is not None):
            self._brain.stop()
    
    def stopListener(self):
        """Stop the Listener instance's daemon"""
        
        if (self._listener is not None):
            self._listener.stop()
    
    def stopSpeaker(self):
        """Stop the Speaker instance's daemon"""
        
        if (self._speaker is not None):
            self._speaker.stop()
            
    def stopWatcher(self):
        """Stop the Watcher instance's daemon"""
        
        if (self._watcher is not None):
            self._watcher.stop()
   
if __name__ == "__main__":

    # A little help to insure our imports work everywhere
    sys.path.insert(0,os.path.abspath(os.path.dirname(__file__)))

    import argparse
    parser = argparse.ArgumentParser(description=kconfig.name, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start all services on the local machine use:\nkaren.py --brain-start --listener-start --speaker-start\n\nMore information available on Github:\nhttps://github.com/lnxusr1/karen\n\nFollow along in the fun at:\nhttps://twitter.com/lnxusr1''')

    parser.add_argument('-v','--version', action='store_true', help="Prints version information")

    brain_group = parser.add_argument_group('Brain Arguments')
    
    brain_group.add_argument('--brain-exec', default=None, help="Executes specified Brain command and exits")
    brain_group.add_argument('--brain-exec-type', default="plain", help="Type of command request (plain, json)")
    brain_group.add_argument('--brain-port', type=int, default=2020, help="Brain's TCP Control Port")
    brain_group.add_argument('--brain-ip', default="0.0.0.0", help="Brain's TCP Control IP Address")
    brain_group.add_argument('--brain-start', action='store_true', help="Starts the BRAIN Daemon")

    listener_group = parser.add_argument_group('Listener Arguments')

    listener_group.add_argument('--listener-exec', default=None, help="Executes specified Listener command and exits")
    listener_group.add_argument('--listener-exec-type', default="plain", help="Type of command request (plain, json)")
    listener_group.add_argument('--listener-port', type=int, default=2022, help="Listener's TCP Control Port")
    listener_group.add_argument('--listener-ip', default="0.0.0.0", help="Listener's TCP Control IP Address")
    listener_group.add_argument('--listener-start', action='store_true', help="Starts the LISTENER Daemon")
    listener_group.add_argument('--listener-silent', action='store_true', help="Disables listener from reading audio on startup")
    listener_group.add_argument('--input-device', type=int, default=None, help="Audio input device (Microphone)")
    listener_group.add_argument('--input-rate', type=int, default=16000, help="Audio input rate")
    listener_group.add_argument('--speaker-model', default="../data/speech/deepspeech-0.7.3-models.pbmm", help="DeepSpeech model file")
    listener_group.add_argument('--padding-ms', type=int, default=450, help="Expected separation between spoken phrases in milliseconds.")
    listener_group.add_argument('--scorer', default=None, help="External scorer file for DeepSpeech")
    listener_group.add_argument('--ratio', type=float, default=0.75, help="Ratio of speech to empty frames when determining phrase context")
    listener_group.add_argument('--vad-aggressiveness', type=int, default=1, help="Noise filtering aggressiveness for VAD (0 thru 3)")

    speaker_group = parser.add_argument_group('Speaker Arguments')
    
    speaker_group.add_argument('--speaker-exec', default=None, help="Executes specified Speaker command and exits")
    speaker_group.add_argument('--speaker-exec-type', default="plain", help="Type of command request (plain, json)")
    speaker_group.add_argument('--speaker-port', type=int, default=2023, help="Speaker's TCP Control Port")
    speaker_group.add_argument('--speaker-ip', default="0.0.0.0", help="Speaker's TCP Control IP Address")
    speaker_group.add_argument('--speaker-start', action='store_true', help="Starts the SPEECH Daemon")
    speaker_group.add_argument('--speaker-visualizer', default=None, help="Visualizer command")
    #speaker_group.add_argument('--speaker-visualizer', default='["xterm","-e","vis"]', help="Visualizer command")

    watcher_group = parser.add_argument_group('Watcher Arguments')
    
    watcher_group.add_argument('--watcher-exec', default=None, help="Executes specified Watcher command and exits")
    watcher_group.add_argument('--watcher-exec-type', default="plain", help="Type of command request (plain, json)")
    watcher_group.add_argument('--watcher-port', type=int, default=2021, help="Watcher's TCP Control Port")
    watcher_group.add_argument('--watcher-ip', default="0.0.0.0", help="Watcher's TCP Control IP Address")
    watcher_group.add_argument('--watcher-start', action='store_true', help="Starts the WATCHER Daemon")
    watcher_group.add_argument('--watcher-model', default="../data/watcher/haarcascade_frontalface_default.xml", help="OpenCV2 Model for Face Recognition")
    watcher_group.add_argument('--watcher-trained', default="../data/tmp/faces.yml", help="Trained faces file")
    watcher_group.add_argument('--watcher-fps', type=int, default=1, help="Number of frames to process per second")
    watcher_group.add_argument('--watcher-rotate', default=None, help="Rotate video image stream")
    watcher_group.add_argument('--watcher-device', type=int, default=0, help="Video Device Index")
    watcher_group.add_argument('--watcher-input-folder', default="../data/faces", help="Folder containing face images for training.")
    watcher_group.add_argument('--watcher-exec-train', action="store_true", help="Execute face training on input folder.")
    
    log_group = parser.add_argument_group('Logging Arguments')
    
    log_group.add_argument('-l','--log-level', default="info", help="Log events (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_group.add_argument('-g','--log-file', default=None, help="Send logs to specified file")
    
    ARGS = parser.parse_args()

    # =============================================
    # Version Info
    
    # Simple "--version" function
    if ARGS.version:
        print(kconfig.name + " v" + str(kconfig.version))
        quit()

    # =============================================
    # Logging Configuration
    
    # Probably a better way to do this, but this is setting the log level for all functions.
    if str(ARGS.log_level).lower() == "debug":
        log_level = logging.DEBUG
    elif str(ARGS.log_level).lower() == "warning":
        log_level = logging.WARNING
    elif str(ARGS.log_level).lower() == "error":
        log_level = logging.ERROR
    elif str(ARGS.log_level).lower() == "critical":
        log_level = logging.CRITICAL
    else:
        log_level = logging.INFO
        
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S %z', filename=ARGS.log_file, format='%(asctime)s - %(levelname)s - %(message)s', level=log_level)

    # =============================================
    # klib.KDaemon.Watcher.train()
        
    # Call to Watcher for training on new Face data set.
    # This Will replace existing training file.
    
    if ARGS.watcher_exec_train:
        w = kd.Watcher(**vars(ARGS))
        w.train()
        quit()

    # =============================================
    # Sends supplied command to the appropriate Daemon via TCP
    # (This could/should be split out into a more generic function.)
    
    # Supports JSON and TEXT formatted requests
    
    bKill = False # Used as a flag to quit if a "exec" command is called.
    
    #TODO: Probably don't need separate objects to call the "sendTCPCommand" function if we rework the If statements.
    
    # Send request to Listener
    if (ARGS.listener_exec is not None) and (str(ARGS.listener_exec).strip() != ""):
        bKill = True
        
        try:
            me = kd.Listener(**vars(ARGS))
            print(me.sendTCPCommand(ARGS.listener_exec, hostname=ARGS.listener_ip, tcp_port=ARGS.listener_port, s_type=ARGS.listener_exec_type))
        except RuntimeError as e:
            print(e)
            
    # Send request to Speaker
    if (ARGS.speaker_exec is not None) and (str(ARGS.speaker_exec).strip() != ""):
        bKill = True
        
        try:
            me = kd.Speaker(**vars(ARGS))
            print(me.sendTCPCommand(ARGS.speaker_exec, hostname=ARGS.speaker_ip, tcp_port=ARGS.speaker_port, s_type=ARGS.speaker_exec_type))
        except RuntimeError as e:
            print(e)

    # Send request to Watcher
    if (ARGS.watcher_exec is not None) and (str(ARGS.watcher_exec).strip() != ""):
        bKill = True
        
        try:
            me = kd.Watcher(**vars(ARGS))
            print(me.sendTCPCommand(ARGS.watcher_exec, hostname=ARGS.watcher_ip, tcp_port=ARGS.watcher_port, s_type=ARGS.watcher_exec_type))
        except RuntimeError as e:
            print(e)
            
    # Send request to Brain
    if (ARGS.brain_exec is not None) and (str(ARGS.brain_exec).strip() != ""):
        bKill = True
        
        try:
            me = kd.Brain(**vars(ARGS))
            print(me.sendTCPCommand(ARGS.brain_exec, hostname=ARGS.brain_ip, tcp_port=ARGS.brain_port, s_type=ARGS.brain_exec_type))
        except RuntimeError as e:
            print(e)

    # If we sent a request to any of the Daemons then we should exit
    if bKill:
        quit()

    # =============================================
    # Karen Management Object
    
    kn = Karen(**vars(ARGS))

    if (ARGS.brain_start):
        kn.startBrain()
    
    if (ARGS.listener_start):
        kn.startListener()
    
    if (ARGS.watcher_start):
        kn.startWatcher()
        
    if (ARGS.speaker_start):
        kn.startSpeaker()
        
    kn.run() # Wait for all daemons to terminate
        
