'''
Project Karen: Synthetic Human
Created on Jul 20, 2020

@author: lnxusr1
@license: MIT Lincense
@summary: Basic skill to audibly respond to questions on faces detected.

'''
from Karen import Skill 
import logging 
import time, json 

class WhoISeeSkill(Skill):
    def __init__(self):
        self._name = "WhoISeeSkill"
        logging.debug("SKILL - " + self._name + "loaded successfully.")
    
    def initialize(self):
        self.register_intent_file("whoisee.intent", self.handle_whoisee_intent)
        
        self.people = []
        try:
            self.people = json.loads(self.getContentsFromVocabFile("people.json"))
        except Exception as e:
            print(e)
            pass
        

    def handle_whoisee_intent(self, message):
        if message.conf == 1.0:
            #print(message)
            data = self.getDataFromBrain("watcher_data")
            t = time.time()
            counter = 0
            person = None
            
            l = len(data)
            if l > 0:
                for z in data:
                    if z["lastFrame"] == True and z["last_seen"] > (t - 5):
                        counter = counter + 1
                        person = z
            
            if counter == 0:
                return self.say("I do not see anyone at the moment.") 
            
            if counter == 1:
                bFound = False
                for item in self.people:
                    if item["id"] == person["idx"]:
                        if "spoken" in item:
                            return self.say("I see "+str(item["spoken"])+".")                        
                        else:
                            return self.say("I see "+str(item["name"])+".")
                        bFound = True

                if bFound == False:
                    return self.say("I see one person.")
            
            if counter > 1:
                return self.say("I see "+str(counter)+" people.")
            
                    
        return { "error": True, "message": "Intent not understood" }
    
    def stop(self):
        return True
    
def create_skill():
    return WhoISeeSkill()