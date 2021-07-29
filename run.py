import os
import karen

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(description=karen.__app_name__ + " v" + karen.__version__, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start the services try:\nrun.py --config [CONFIG_FILE]\n\nMore information available at:\nhttp://projectkaren.ai''')
    #parser.add_argument('--locale', default="en_us", help="Language Locale")

    parser.add_argument('-c','--config', default=None, help="Configuration file")
    parser.add_argument('-v','--version', action="store_true", help="Print Version")
    parser.add_argument('--watcher', action="store_true", help="Use watcher default configuration")
    
    logging_group = parser.add_argument_group('Logging Arguments')
    
    logging_group.add_argument('--log-level', default="info", help="Options are debug, info, warning, error, and critical")
    logging_group.add_argument('--log-file', default=None, help="Redirects all logging messages to the specified file")
    
    ARGS = parser.parse_args()
    
    if ARGS.version:
        print(karen.__app_name__,"v"+karen.__version__)
        quit()

    configFile = ARGS.config
    if configFile is not None:
        configFile = os.path.abspath(ARGS.config)
        if not os.path.isfile(configFile):
            raise Exception("Configuration file does not exist.")
            quit(1)
    else:
        if ARGS.watcher:
            configFile = "video"
            
    karen.start(configFile=configFile, log_level=ARGS.log_level, log_file=ARGS.log_file)