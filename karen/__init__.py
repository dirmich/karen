import os, sys
sys.path.insert(0,os.path.join(os.path.abspath(os.path.dirname(__file__)), "skills"))

# version as tuple for simple comparisons 
VERSION = (0, 5, 1) 
# string created from tuple to avoid inconsistency 
__version__ = ".".join([str(x) for x in VERSION])
__app_name__ = "Project Karen"

from .listener import Listener
from .speaker import Speaker
#from .engine import Engine
from .device import DeviceContainer
from .brain import Brain
from .skillmanager import Skill
from .shared import dayPart
