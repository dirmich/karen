import os, logging
import karen
import karen.watcher

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(description=karen.__app_name__ + " v" + karen.__version__, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start the services try:\nrun.py --config [CONFIG_FILE]\n\nMore information available at:\nhttp://projectkaren.ai''')
    #parser.add_argument('--locale', default="en_us", help="Language Locale")

    parser.add_argument('-f','--training-source-folder', required=True, help="Training Source Folder")
    parser.add_argument('--classifier-file', default=None, help="Classifier definition")
    parser.add_argument('--recognizer-file', default=None, help="Recognizer YAML file")
    parser.add_argument('--names-file', default=None, help="Friendly names file mapping for recognizer")

    parser.add_argument('-v','--version', action="store_true", help="Print Version")
    
    logging_group = parser.add_argument_group('Logging Arguments')
    
    logging_group.add_argument('--log-level', default="info", help="Options are debug, info, warning, error, and critical")
    logging_group.add_argument('--log-file', default=None, help="Redirects all logging messages to the specified file")
    
    ARGS = parser.parse_args()
    
    if ARGS.version:
        print(karen.__app_name__,"v"+karen.__version__)
        quit()
        
    log_level = ARGS.log_level
    log_file = ARGS.log_file

    logging_level = logging.DEBUG
    if str(log_level).lower() == "debug":
        logging_level = logging.DEBUG 
    elif str(log_level).lower() == "info":
        logging_level = logging.INFO
    elif str(log_level).lower() == "warning":
        logging_level = logging.WARNING
    elif str(log_level).lower() == "error":
        logging_level = logging.ERROR
    elif str(log_level).lower() == "critical":
        logging_level = logging.CRITICAL
        
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S %z', filename=log_file, format='%(asctime)s %(name)-12s - %(levelname)-9s - %(message)s', level=logging.DEBUG)
    
    # Loggers we don't control
    logging.getLogger("requests").setLevel(logging_level)
    logging.getLogger("urllib3").setLevel(logging_level)
    logging.getLogger("PIL.TiffImagePlugin").setLevel(logging.INFO)
    # Loggers that are built into Karen
    logging.getLogger("CTYPES").setLevel(logging_level)
    logging.getLogger("HTTP").setLevel(logging_level)
    logging.getLogger("CONTAINER").setLevel(logging_level)
    logging.getLogger("LISTENER").setLevel(logging_level)
    logging.getLogger("BRAIN").setLevel(logging_level)
    logging.getLogger("SKILLMANAGER").setLevel(logging_level)
    logging.getLogger("WATCHER").setLevel(logging_level)

    sourceFolder = ARGS.training_source_folder
    sourceFolder = os.path.abspath(sourceFolder)
    if not os.path.isdir(sourceFolder):
        raise Exception("Source folder does not exist.")
        quit(1)
        
    watcher = karen.watcher.Watcher(classifierFile=ARGS.classifier_file, recognizerFile=ARGS.recognizer_file, namesFile=ARGS.names_file, trainingSourceFolder=sourceFolder)
    watcher.train()