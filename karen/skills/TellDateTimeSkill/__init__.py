'''
Project Karen: Synthetic Human
Created on Jul 20, 2020
@author: lnxusr1
@license: MIT License
@summary: Basic skill to respond audibly to questions about date and time
'''
from karen import Skill, dayPart
import logging, time

class TellDateTimeSkill(Skill):
    """
    Skill to give the date and time.
    """
    
    def __init__(self):
        """
        Tell Date and Time Skill Initialization
        """
        
        self._name = "TellDateTimeSkill"
        self.logger = logging.getLogger("SKILL")
        self.logger.debug(self._name + "loaded successfully.")
    
    def initialize(self):
        """
        Load intent files for Tell Date Time Skill
        
        Returns:
            (bool): True on success else raises an exception
        """
        
        self.register_intent_file("telltime.intent", self.handle_telltime_intent)
        self.register_intent_file("telldate.intent", self.handle_telldate_intent)
        return True

    def handle_telltime_intent(self, message):
        """
        Primary function for intent matches when a TIME intent is detected.  Called by skill manager.
        
        Args:
            message (str):  text that triggered the intent
            
        Returns:
            (bool): True on success or False on failure
        """
        
        if message.conf == 1.0:
            
            dp = dayPart().lower()
            if dp == "night":
                dp = " P M"
            else:
                dp = " in the " + dp

            text = "It is " + time.strftime("%l") + ":" + time.strftime("%M") + dp
             
            return self.say(text)
                    
        return False
    
    def handle_telldate_intent(self, message):
        """
        Primary function for intent matches when a DATE intent is detected.  Called by skill manager.
        
        Args:
            message (str):  text that triggered the intent
            
        Returns:
            (bool): True on success or False on failure
        """

        if message.conf == 1.0:
            text = "It is " + time.strftime("%A, %B %d")
            return self.say(text)
        
        return True
    
    def stop(self):
        """
        Method to stop any daemons created during startup/initialization for this skill.
        
        Returns:
            (bool):  True on success and False on failure
        """
        
        return True
    
def create_skill():
    """
    Method to create the instance of this skill for delivering to the skill manager
    
    Returns:
        (object): TellDateTimeSkill instantiated class object
    """
    
    return TellDateTimeSkill()