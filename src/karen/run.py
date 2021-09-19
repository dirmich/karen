import sys
import os
from karen import __version__, __app_name__, start

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(description=__app_name__ + " v" + __version__, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start the services try:\nrun.py --config [CONFIG_FILE]\n\nMore information available at:\nhttp://projectkaren.ai''')
    #parser.add_argument('--locale', default="en_us", help="Language Locale")

    parser.add_argument('-c','--config', default=None, help="Configuration file")
    parser.add_argument('-v','--version', action="store_true", help="Print Version")
    parser.add_argument('--video', action="store_true", help="Use watcher default configuration")
    
    listener_group = parser.add_argument_group('Listener Arguments')
    
    listener_group.add_argument('--download-models', action="store_true", help="Download listener models")
    listener_group.add_argument('--model-version', default=None, help="Deepspeech Model Version")
    listener_group.add_argument('--model-type', default="pbmm", help="Deepspeech Model Type as pbmm or tflite")
    listener_group.add_argument('--include-scorer', action="store_true", help="Include scorer model")
    listener_group.add_argument('--overwrite', action="store_true", help="Overwrite models")
    
    logging_group = parser.add_argument_group('Logging Arguments')
    
    logging_group.add_argument('--log-level', default="info", help="Options are debug, info, warning, error, and critical")
    logging_group.add_argument('--log-file', default=None, help="Redirects all logging messages to the specified file")
    
    ARGS = parser.parse_args()
    
    if ARGS.version:
        print(__app_name__,"v"+__version__)
        quit()
        
    if ARGS.download_models:
        try:
            import karen_listener
            if karen_listener.download_models(version=ARGS.model_version, model_type=ARGS.model_type, include_scorer=ARGS.include_scorer, overwrite=ARGS.overwrite):
                print("Models downloaded successfully.")
                quit()
        except:
            raise
        
        print("Error downloading models.")
        quit()
            

    configFile = ARGS.config
    if configFile is not None:
        configFile = os.path.abspath(ARGS.config)
        if not os.path.isfile(configFile):
            raise Exception("Configuration file does not exist.")
            quit(1)
    else:
        if ARGS.video:
            configFile = "video"
            
    start(configFile=configFile, log_level=ARGS.log_level, log_file=ARGS.log_file)
