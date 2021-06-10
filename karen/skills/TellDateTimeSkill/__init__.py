'''
Project Karen: Synthetic Human
Created on Jul 20, 2020
@author: lnxusr1
@license: MIT License
@summary: Basic skill to respond audibly to questions about time
'''
from karen import Skill, dayPart
import logging, time

class TellDateTimeSkill(Skill):
    def __init__(self):
        self._name = "TellDateTimeSkill"
        logging.debug("SKILL - " + self._name + "loaded successfully.")
    
    def initialize(self):
        self.register_intent_file("telltime.intent", self.handle_telltime_intent)
        self.register_intent_file("telldate.intent", self.handle_telldate_intent)
        

    def handle_telltime_intent(self, message):
        if message.conf == 1.0:
            
            dp = dayPart().lower()
            if dp == "night":
                dp = " P M"
            else:
                dp = " in the " + dp

            text = "It is " + time.strftime("%l") + ":" + time.strftime("%M") + dp
             
            return self.say(text)
                    
        return { "error": True, "message": "Intent not understood" }
    
    def handle_telldate_intent(self, message):
        if message.conf == 1.0:
            text = "It is " + time.strftime("%A, %B %d")
            return self.say(text)
        
        return { "error": False, "message": "OK" }
    
    def stop(self):
        return True
    
def create_skill():
    return TellDateTimeSkill()