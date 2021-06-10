'''
Project Karen: Synthetic Human
Created on Jul 27, 2020
@author: lnxusr1
@license: MIT License
@summary: Knock Knock joke skill.
'''
from karen import Skill 
import logging 

class KnockKnockSkill(Skill):
    def __init__(self):
        self._name = "KnockKnockSkill"
        logging.debug("SKILL - " + self._name + "loaded successfully.")
    
    def initialize(self):
        self.register_intent_file("knockknock.intent", self.handle_knockknock_intent)
        

    def handle_knockknock_q2(self, message):
        text = self.getMessageFromDialog("knockknock.dialog")
        if text != "":
            return self.say(text)
        else:
            return self.say("ha ha ha.")
        
    def handle_knockknock_q1(self, message):
        return self.ask(str(message) + " who?", self.handle_knockknock_q2, timeout=10)

    def handle_knockknock_intent(self, message):
        #print(message)
            
        return self.ask("Who's there?", self.handle_knockknock_q1, timeout=10)
        
        #return { "error": True, "message": "Intent not understood" }
    
    def stop(self):
        return True
    
def create_skill():
    return KnockKnockSkill()