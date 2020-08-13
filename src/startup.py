'''
Project Karen: Startup
Created on July 12, 2020

@author: lnxusr1
@license: MIT License
@summary: Startup Process

'''

import os, logging
from Karen import Brain, Speaker, Watcher, Listener, threaded, Version

@threaded
def startBrain(config):
    d = Brain(**config)
    d.run()

@threaded
def startSpeaker(config):
    d = Speaker(**config)
    d.run()

@threaded
def startWatcher(config):
    d = Watcher(**config)
    d.run()
    
@threaded
def startListener(config):
    d = Listener(**config)
    d.run()

if __name__ == "__main__":
    
    # A little help to insure our imports work everywhere
    #sys.path.insert(0,os.path.abspath(os.path.dirname(__file__)))
    

    import argparse
    parser = argparse.ArgumentParser(description=Version.name, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start all services on the local machine use:\nkaren.py --brain-start --listener-start --speaker-start\n\nMore information available on Github:\nhttps://github.com/lnxusr1/karen\n\nFollow along in the fun at:\nhttps://twitter.com/lnxusr1''')

    parser.add_argument('-v','--version', action='store_true', help="Prints version information")
    #parser.add_argument('--locale', default="en_us", help="Language Locale")
    
    starter_group = parser.add_argument_group('Daemon Start Arguments')
    
    starter_group.add_argument('--brain-start', action='store_true', help="Starts the Brain Daemon")
    starter_group.add_argument('--listener-start', action='store_true', help="Starts the Listener Daemon")
    starter_group.add_argument('--speaker-start', action='store_true', help="Starts the Speaker Daemon")
    starter_group.add_argument('--watcher-start', action='store_true', help="Starts the Watcher Daemon")
    
    
    ssl_group = parser.add_argument_group('Security Arguments')
    
    ssl_group.add_argument('--use-http', action='store_true', help="Force to use HTTP instead of HTTPS")
    ssl_group.add_argument('--ssl-keyfile', default=None, help="SSL Key PEM file")
    ssl_group.add_argument('--ssl-certfile', default=None, help="SSL Key PEM file")
    
    brain_group = parser.add_argument_group('Brain Arguments')
    
    brain_group.add_argument('--brain-port', type=int, default=2020, help="Brain's TCP Control Port")
    brain_group.add_argument('--brain-ip', default="0.0.0.0", help="Brain's TCP Control IP Address")
    brain_group.add_argument('--web-folder', default="../webgui", help="Folder for Web Control GUI")
    brain_group.add_argument('--mem-path', default=None, help="Shared Memory Pool")

    listener_group = parser.add_argument_group('Listener Arguments')
    
    listener_group.add_argument('--listener-port', type=int, default=2022, help="Listener's TCP Control Port")
    listener_group.add_argument('--listener-ip', default="0.0.0.0", help="Listener's TCP Control IP Address")
    listener_group.add_argument('--silent', action='store_true', help="Disables listener from reading audio on startup")
    listener_group.add_argument('--listener-device', type=int, default=None, help="Audio input device (Microphone)")
    listener_group.add_argument('--input-rate', type=int, default=16000, help="Audio input rate")
    listener_group.add_argument('--listener-model', default="../models/speech/deepspeech-0.7.4-models.pbmm", help="DeepSpeech model file")
    listener_group.add_argument('--padding-ms', type=int, default=350, help="Expected separation between spoken phrases in milliseconds.")
    listener_group.add_argument('--scorer', default=None, help="External scorer file for DeepSpeech")
    listener_group.add_argument('--ratio', type=float, default=0.75, help="Ratio of speech to empty frames when determining phrase context")
    listener_group.add_argument('--vad-aggressiveness', type=int, default=1, help="Noise filtering aggressiveness for VAD (0 thru 3)")

    speaker_group = parser.add_argument_group('Speaker Arguments')
    
    speaker_group.add_argument('--speaker-port', type=int, default=2023, help="Speaker's TCP Control Port")
    speaker_group.add_argument('--speaker-ip', default="0.0.0.0", help="Speaker's TCP Control IP Address")
    speaker_group.add_argument('--visualizer', default=None, help="Visualizer command")
    #speaker_group.add_argument('--visualizer', default='["xterm","-e","vis"]', help="Visualizer command")

    watcher_group = parser.add_argument_group('Watcher Arguments')
    
    watcher_group.add_argument('--watcher-port', type=int, default=2021, help="Watcher's TCP Control Port")
    watcher_group.add_argument('--watcher-ip', default="0.0.0.0", help="Watcher's TCP Control IP Address")
    watcher_group.add_argument('--watcher-model', default=None, help="OpenCV2 Model for Face Recognition")
    watcher_group.add_argument('--trained', default=None, help="Trained faces file")
    watcher_group.add_argument('--fps', type=int, default=1, help="Number of frames to process per second")
    watcher_group.add_argument('--rotate', default=None, help="Rotate video image stream")
    watcher_group.add_argument('--watcher-device', type=int, default=0, help="Video Device Index")
    watcher_group.add_argument('--input-folder', default=None, help="Folder containing face images for training.")
    watcher_group.add_argument('--exec-train', action="store_true", help="Execute face training on input folder.")

    log_group = parser.add_argument_group('Logging Arguments')
    
    log_group.add_argument('-l','--log-level', default="info", help="Log events (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_group.add_argument('-g','--log-file', default=None, help="Send logs to specified file")
    
    ARGS = parser.parse_args()

    ARGS.web_folder = os.path.abspath(ARGS.web_folder)
    if ARGS.mem_path is not None:
        ARGS.mem_path = os.path.abspath(ARGS.mem_path)

    # =============================================
    # Version Info
    
    # Simple "--version" function
    if ARGS.version:
        print(Version.name + " v" + str(Version.rev))
        quit()

    # =============================================
    # Logging Configuration
    
    log_level_all = logging.WARNING
    
    # Probably a better way to do this, but this is setting the log level for all functions.
    if str(ARGS.log_level).lower() == "debug":
        log_level = logging.DEBUG
    elif str(ARGS.log_level).lower() == "warning":
        log_level = logging.WARNING
    elif str(ARGS.log_level).lower() == "error":
        log_level = logging.ERROR
    elif str(ARGS.log_level).lower() == "critical":
        log_level = logging.CRITICAL
    elif str(ARGS.log_level).lower() == "debug_all":
        log_level = logging.DEBUG 
        log_level_all = logging.DEBUG 
    else:
        log_level = logging.INFO
        
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S %z', filename=ARGS.log_file, format='%(asctime)s - %(levelname)s - %(message)s', level=log_level)
    logging.getLogger("requests").setLevel(log_level_all)
    logging.getLogger("urllib3").setLevel(log_level_all)

    
    # =============================================
    # Configure
    
    brain_config = {
        "use_http": ARGS.use_http,
        "ssl_keyfile": ARGS.ssl_keyfile,
        "ssl_certfile": ARGS.ssl_certfile,
        "port": ARGS.brain_port,
        "ip": ARGS.brain_ip,
        "mem_path": ARGS.mem_path,
        "web_folder": ARGS.web_folder,
        "log_level": ARGS.log_level,
        "log_file": ARGS.log_file
    }
    
      
    speaker_config = {
        "use_http": ARGS.use_http,
        "ssl_keyfile": ARGS.ssl_keyfile,
        "ssl_certfile": ARGS.ssl_certfile,
        "brain_ip": ARGS.brain_ip,
        "brain_port": ARGS.brain_port,
        "port": ARGS.speaker_port,
        "ip": ARGS.speaker_ip,
        "visualizer": ARGS.visualizer,
        "log_level": ARGS.log_level,
        "log_file": ARGS.log_file
    }

    listener_config = {
        "use_http": ARGS.use_http,
        "ssl_keyfile": ARGS.ssl_keyfile,
        "ssl_certfile": ARGS.ssl_certfile,
        "brain_ip": ARGS.brain_ip,
        "brain_port": ARGS.brain_port,
        "port": ARGS.listener_port,
        "ip": ARGS.listener_ip,
        "silent": ARGS.silent,
        "input_device": ARGS.listener_device,
        "input_rate": ARGS.input_rate,
        "model": ARGS.listener_model,
        "padding_ms": ARGS.padding_ms,
        "scorer": ARGS.scorer,
        "ratio": ARGS.ratio,
        "vad_aggressiveness": ARGS.vad_aggressiveness,
        "log_level": ARGS.log_level,
        "log_file": ARGS.log_file
    }
    
    watcher_config = {
        "use_http": ARGS.use_http,
        "ssl_keyfile": ARGS.ssl_keyfile,
        "ssl_certfile": ARGS.ssl_certfile,
        "brain_ip": ARGS.brain_ip,
        "brain_port": ARGS.brain_port,
        "port": ARGS.watcher_port,
        "ip": ARGS.watcher_ip,
        "model": ARGS.watcher_model,
        "trained": ARGS.trained,
        "fps": ARGS.fps,
        "rotate": ARGS.rotate,
        "device": ARGS.watcher_device,
        "input_folder": ARGS.input_folder,
        "log_level": ARGS.log_level,
        "log_file": ARGS.log_file
    }
    
    # =============================================
    # Check if we need to train.
    
    if ARGS.exec_train:
        d = Watcher(**watcher_config)
        d.train()
        
        if ARGS.exec_train:
            quit()
    
    t_brain = None
    t_listener = None 
    t_speaker = None
    t_watcher = None
    
    
    if ARGS.brain_start:
        t_brain = startBrain(brain_config)
        
        # Hold off for a couple of seconds so the brain can spin up.
        import time
        time.sleep(2)
    
    if ARGS.speaker_start:
        t_speaker = startSpeaker(speaker_config)
    
    if ARGS.watcher_start:
        t_watcher = startWatcher(watcher_config)

    if ARGS.listener_start:
        t_listener = startListener(listener_config)
    
    try:
    
        if t_brain is not None:
            t_brain.join()
            
        if t_listener is not None:
            t_listener.join()
            
        if t_speaker is not None:
            t_speaker.join()
            
        if t_watcher is not None:
            t_watcher.join()
        
    except KeyboardInterrupt:
        pass
        