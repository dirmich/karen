'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Core Library
'''

import os, sys
sys.path.insert(0,os.path.join(os.path.abspath(os.path.dirname(__file__)), "skills"))

# version as tuple for simple comparisons 
VERSION = (0, 5, 1) 
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