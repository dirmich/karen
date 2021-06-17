'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Core Library
'''

import os, sys
import logging 
import json 

sys.path.insert(0,os.path.join(os.path.abspath(os.path.dirname(__file__)), "skills"))

# version as tuple for simple comparisons 
VERSION = (0, 5, 4) 
# string created from tuple to avoid inconsistency 
__version__ = ".".join([str(x) for x in VERSION])
__app_name__ = "Project Karen"

# Imports for built-in features
from .listener import Listener
from .speaker import Speaker
from .device import DeviceContainer
from .brain import Brain
from .skillmanager import Skill, SkillManager
from .shared import dayPart

def _getImport(libs, val):
    """
    Dynamically imports a library into memory for referencing during configuration file parsing.
    
    Args:
        libs (list):  The list of libraries already imported.
        val (str):  The name of the new library to import.
    
    Returns:
        (str): The name of the newly imported library.  If library is already imported then returns None.
    """

    if val is not None and isinstance(val,str) and val.strip() != "":
        if "." in val:
            parts = val.split(".")
            parts.pop()
            ret = ".".join(parts)
            if ret in libs:
                return None

            libs.append(ret)
            return ret

    return None
        
def start(configFile, log_level="info", log_file=None):
    """
    Static method to start a new instance of karen based on a provided configuration file.
    
    Args:
        configFile (str):  Path and Name of the JSON configuration file.
        log_level (str):  The level of logging to provide (critical, error, warning, info, and debug). )ptional)
        log_file (str):  Path and Name of the log file to create (otherwise prints all messages to stderr). (optional)
    """
    
    configFile = os.path.abspath(configFile)
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
    importedLibs = ["karen"]
    skillFolder = None
    
    # Location for 3rd party libraries.  We add to system path to make imports automatic.
    if "settings" in myConfig and "libraryFolder" in myConfig["settings"] and myConfig["settings"]["libraryFolder"] is not None:
        if os.path.isdir(str(myConfig["settings"]["libraryFolder"])):
            sys.path.insert(0,os.path.abspath(str(myConfig["settings"]["libraryFolder"])))

    if "settings" in myConfig and "skillsFolder" in myConfig["settings"] and myConfig["settings"]["skillsFolder"] is not None:
        if os.path.isdir(str(myConfig["settings"]["skillsFolder"])):
            sys.path.insert(0,os.path.abspath(str(myConfig["settings"]["skillsFolder"])))
            skillFolder = os.path.abspath(str(myConfig["settings"]["skillsFolder"]))

    # Establishing the BRAIN instance
    if "brain" in myConfig:
        tcp_port=myConfig["brain"]["tcp_port"] if "tcp_port" in myConfig["brain"] and myConfig["brain"]["tcp_port"] is not None else 8080
        hostname=myConfig["brain"]["hostname"] if "hostname" in myConfig["brain"] and myConfig["brain"]["hostname"] is not None else "localhost"
        use_ssl=myConfig["brain"]["ssl"]["use_ssl"] if "ssl" in myConfig["brain"] and "use_ssl" in myConfig["brain"]["ssl"] else False
        ssl_cert_file=myConfig["brain"]["ssl"]["cert_file"] if "ssl" in myConfig["brain"] and "cert_file" in myConfig["brain"]["ssl"] else None
        ssl_key_file=myConfig["brain"]["ssl"]["key_file"] if "ssl" in myConfig["brain"] and "key_file" in myConfig["brain"]["ssl"] else None

        # A BRAIN segment must always exist because we must create a brain_url
        brain_url = "http" + ("s" if use_ssl else "") + "://" + hostname + ":" + str(tcp_port)

        if not use_ssl:
            ssl_cert_file = None
            ssl_key_file = None 
            
        if "start" not in myConfig["brain"] or myConfig["brain"]["start"]:        

            brain = Brain(
                    tcp_port=tcp_port,
                    hostname=hostname,
                    ssl_cert_file=ssl_cert_file,
                    ssl_key_file=ssl_key_file,
                    skill_folder=skillFolder
                )
    
            if "commands" in myConfig["brain"] and isinstance(myConfig["brain"]["commands"],list):
                for command in myConfig["brain"]["commands"]:
                    if "type" not in command or "function" not in command:
                        print("Invalid handler specified " + str(command))
                        quit(1)
                    
                    friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
    
                    myImport = _getImport(importedLibs, command["function"])
                    if myImport is not None:
                        exec("import "+str(myImport))
    
                    eval("brain.setHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")
    
            if "data" in myConfig["brain"] and isinstance(myConfig["brain"]["data"],list):
                for command in myConfig["brain"]["data"]:
                    if "type" not in command or "function" not in command:
                        print("Invalid handler specified " + str(command))
                        quit(1)
                    
                    friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
    
                    myImport = _getImport(importedLibs, command["function"])
                    if myImport is not None:
                        exec("import "+str(myImport))
    
                    eval("brain.setDataHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")
    
            brain.start()

    # Establishing the DEVICE CONTAINER instance
    if "container" in myConfig:

        if "start" not in myConfig["container"] or myConfig["container"]["start"]:        

            if brain_url is None:
                raise Exception("Brain URL cannot be determined for device container.")
                quit(1)

            container = DeviceContainer(
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
                        
                    strType = (device["type"]).lstrip("karen.")
    
                    myImport = _getImport(importedLibs, device["type"])
                    if myImport is not None:
                        exec("import "+str(myImport))
    
                    friendlyName = device["friendlyName"] if "friendlyName" in device else None
                    autoStart = device["autoStart"] if "autoStart" in device else True
                    devParams = device["parameters"] if "parameters" in device and isinstance(device["parameters"], dict) else {}
                    newDevice = eval(str(strType) + "(callback=container.callbackHandler, **devParams)")
                    
                    container.addDevice(device["type"], newDevice, friendlyName=friendlyName, autoStart=autoStart)
    
            if "commands" in myConfig["container"] and isinstance(myConfig["container"]["commands"],list):
                for command in myConfig["container"]["commands"]:
                    if "type" not in command or "function" not in command:
                        print("Invalid handler specified " + str(command))
                        quit(1)
                    
                    friendlyName = ", friendlyName=\"" + str(command["friendlyName"]) + "\"" if "friendlyName" in command and command["friendlyName"] is not None else ""
    
                    myImport = _getImport(importedLibs, command["function"])
                    if myImport is not None:
                        exec("import "+str(myImport))
    
                    eval("container.setHandler(\"" + str(command["type"]) + "\", " + str(command["function"]) + friendlyName + ")")
    
            container.start()

    if brain is not None:
        brain.wait()
    
    if container is not None:
        container.wait()
        
    return True