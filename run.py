import logging 
import karen
import karen.handlers 
import sys
import os
import json 

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(description=karen.__app_name__ + " v" + karen.__version__, formatter_class=argparse.RawTextHelpFormatter, epilog='''To start the services try:\nrun.py --config [CONFIG_FILE]\n\nMore information available at:\nhttp://projectkaren.ai''')
    #parser.add_argument('--locale', default="en_us", help="Language Locale")

    parser.add_argument('-c','--config', required=True, help="Configuration file")
    
    logging_group = parser.add_argument_group('Logging Arguments')
    
    logging_group.add_argument('--log-level', default="info", help="Options are debug, info, warning, error, and critical")
    logging_group.add_argument('--log-file', default=None, help="Redirects all logging messages to the specified file")
    
    ARGS = parser.parse_args()

    configFile = os.path.abspath(ARGS.config)
    if not os.path.isfile(configFile):
        raise Exception("Configuration file does not exist.")
        quit(1)
        
    try:
        with open(configFile, 'r') as fp:
            myConfig = json.load(fp)
    except:
        raise Exception("Configuration file does not to be properly formatted")
        quit(1)
        
    logging_level = logging.DEBUG
    if str(ARGS.log_level).lower() == "debug":
        logging_level = logging.DEBUG 
    elif str(ARGS.log_level).lower() == "info":
        logging_level = logging.INFO
    elif str(ARGS.log_level).lower() == "warning":
        logging_level = logging.WARNING
    elif str(ARGS.log_level).lower() == "error":
        logging_level = logging.ERROR
    elif str(ARGS.log_level).lower() == "critical":
        logging_level = logging.CRITICAL
        
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S %z', filename=ARGS.log_file, format='%(asctime)s %(name)-12s - %(levelname)-9s - %(message)s', level=logging.DEBUG)
    
    # Loggers we don't control
    logging.getLogger("requests").setLevel(logging_level)
    logging.getLogger("urllib3").setLevel(logging_level)
    
    # Loggers that are built into Karen
    logging.getLogger("CTYPES").setLevel(logging_level)
    logging.getLogger("HTTP").setLevel(logging_level)
    logging.getLogger("CONTAINER").setLevel(logging_level)
    logging.getLogger("LISTENER").setLevel(logging_level)
    logging.getLogger("BRAIN").setLevel(logging_level)
    logging.getLogger("SKILLMANAGER").setLevel(logging_level)

    # Process configuration file and start engines as appropriate.
    brain = None
    container = None 
    
    if "brain" in myConfig:
        tcp_port=myConfig["brain"]["tcp_port"] if "tcp_port" in myConfig["brain"] and myConfig["brain"]["tcp_port"] is not None else 8080
        hostname=myConfig["brain"]["hostname"] if "hostname" in myConfig["brain"] and myConfig["brain"]["hostname"] is not None else "localhost"
        ssl_cert_file=myConfig["brain"]["ssl"]["cert_file"] if "ssl" in myConfig["brain"] and "cert_file" in myConfig["brain"]["ssl"] else None
        ssl_key_file=myConfig["brain"]["ssl"]["key_file"] if "ssl" in myConfig["brain"] and "key_file" in myConfig["brain"]["ssl"] else None

        brain_url = "http" + ("s" if ssl_cert_file is not None and ssl_key_file is not None else "") + "://" + hostname + ":" + str(tcp_port)

        brain = karen.Brain(
                tcp_port=tcp_port,
                hostname=hostname,
                ssl_cert_file=ssl_cert_file,
                ssl_key_file=ssl_key_file
            )

        if "commands" in myConfig["brain"] and isinstance(myConfig["brain"]["commands"],list):
            for command in myConfig["brain"]["commands"]:
                if "type" not in command or "function" not in command:
                    print("Invalid handler specified " + str(command))
                    quit(1)
                
                friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
                eval("brain.setHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")

        if "data" in myConfig["brain"] and isinstance(myConfig["brain"]["data"],list):
            for command in myConfig["brain"]["data"]:
                if "type" not in command or "function" not in command:
                    print("Invalid handler specified " + str(command))
                    quit(1)
                
                friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
                eval("brain.setDataHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")

        if "start" not in myConfig["brain"] or myConfig["brain"]["start"]:        
            brain.start()

    if "container" in myConfig:
        if brain_url is None:
            raise Exception("Brain URL cannot be determined for device container.")
            quit(1)
            
        container = karen.DeviceContainer(
                tcp_port=myConfig["container"]["tcp_port"] if "tcp_port" in myConfig["container"] else None,
                hostname=myConfig["container"]["hostname"] if "hostname" in myConfig["container"] else None,
                ssl_cert_file=myConfig["container"]["ssl"]["cert_file"] if "ssl" in myConfig["container"] and "cert_file" in myConfig["container"]["ssl"] else None,
                ssl_key_file=myConfig["container"]["ssl"]["key_file"] if "ssl" in myConfig["container"] and "key_file" in myConfig["container"]["ssl"] else None,
                brain_url=brain_url
            )
        
        if "devices" in myConfig["container"] and isinstance(myConfig["container"]["devices"],list):
            for device in myConfig["container"]["devices"]:
                if "type" not in device or device["type"] is None:
                    print("Invalid device specified.  No type given.")
                    quit(1)

                if (not (device["type"]).startswith("karen.") and not device["type"].replace("karen.","").contains(".")):
                    if "settings" in myConfig and "libraryFolder" in myConfig["settings"]:
                        if myConfig["settings"]["libraryFolder"] is not None and os.path.isdir(str(myConfig["settings"]["libraryFolder"])):
                            sys.path.insert(0,os.path.abspath(str(myConfig["settings"]["libraryFolder"])))
                        
                    importPath = str(device["type"]).split(".")
                    importPath.pop() # remove the last item which shoudl be a class
                    eval("import "+(".").join(importPath))

                friendlyName = device["friendlyName"] if "friendlyName" in device else None
                autoStart = device["autoStart"] if "autoStart" in device else True
                devParams = device["parameters"] if "parameters" in device and isinstance(device["parameters"], dict) else {}
                newDevice = eval(str(device["type"]) + "(callback=container.callbackHandler, **devParams)")
                
                container.addDevice(device["type"], newDevice, friendlyName=friendlyName, autoStart=autoStart)

        if "commands" in myConfig["container"] and isinstance(myConfig["container"]["commands"],list):
            for command in myConfig["container"]["commands"]:
                if "type" not in command or "function" not in command:
                    print("Invalid handler specified " + str(command))
                    quit(1)
                
                friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
                eval("container.setHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")

        
        if "start" not in myConfig["container"] or myConfig["container"]["start"]:        
            container.start()

    if brain is not None:
        brain.wait()
    
    if container is not None:
        container.wait()