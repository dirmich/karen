# Custom Devices

You can build your own devices by inheriting karen.templates.DeviceTemplate which has the following basic structure:

```
from karen.templates import DeviceTemplate

class MyCustomDevice(DeviceTemplate):
    def __init__(self,
            parent=None,
            callback=None):
        
        self.parent = parent
        self.callback = callback
        self._isRunning = False 
        
    @property
    def accepts(self):
        return ["start","stop"]
    
    @property
    def isRunning(self):
        return self._isRunning
    
    def start(self, httpRequest=None):
        self._isRunning = True
        return True
    
    def stop(self, httpRequest=None):
        self._isRunning = False
        return True
```