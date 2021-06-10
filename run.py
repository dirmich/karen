import logging 
import karen 
import time 
import os

if __name__ == "__main__":
    
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S %z', filename=None, format='%(asctime)s %(name)-10s - %(levelname)-9s - %(message)s', level=logging.DEBUG)
    
    # Loggers we don't control
    logging.getLogger("requests").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    
    # Loggers that are built into Karen
    logging.getLogger("CTYPES").setLevel(logging.DEBUG)
    logging.getLogger("HTTP").setLevel(logging.DEBUG)
    logging.getLogger("CONTAINER").setLevel(logging.DEBUG)
    logging.getLogger("LISTENER").setLevel(logging.DEBUG)
    logging.getLogger("BRAIN").setLevel(logging.DEBUG)
    logging.getLogger("SKILLMANAGER").setLevel(logging.DEBUG)

    brain = karen.Brain()
    brain.start()

    client = karen.DeviceContainer()
    
    local_path = os.path.join(os.path.dirname(__file__), "models")
    
    listener = karen.Listener(
        callback=client.callbackHandler, 
        speechModel=os.path.join(local_path, 'speech', 'deepspeech-0.9.3-models.pbmm'), 
        speechScorer=os.path.join(local_path, 'speech', 'deepspeech-0.9.3-models.scorer')
    )
    
    listener.start()
    time.sleep(2) # so that listener comes online and all messages are logged properly (SilenceStream could hide log messages on initial load).
    client.addDevice("listener",listener)
    
    speaker = karen.Speaker(
        callback=client.callbackHandler
    )

    client.start()
    client.addDevice("speaker",speaker)

    client.wait(seconds=30)
    brain.stop()
