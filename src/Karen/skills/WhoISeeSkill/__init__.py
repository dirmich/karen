from Karen import Skill 
import logging 
import time 

class WhoISeeSkill(Skill):
    def __init__(self):
        self._name = "WhoISeeSkill"
        logging.debug("SKILL - " + self._name + "loaded successfully.")
    
    def initialize(self):
        self.register_intent_file("whoisee.intent", self.handle_whoisee_intent)
        

    def handle_whoisee_intent(self, message):
        if message.conf == 1.0:
            #print(message)
            data = self.brain.getWatcherData()
            t = time.time()
            counter = 0
            person = None
            
            l = len(data)
            if l > 0:
                for z in data:
                    if z["lastFrame"] == True or z["last_seen"] > t - 5:
                        counter = counter + 1
                        person = z
            
            if counter == 0:
                return self.say("I do not see anyone at the moment.") 
            
            if counter == 1:
                if person["idx"] == 1:
                    return self.say("I see lnx user 1.")
                else:
                    return self.say("I see one person.")
            
            if counter > 1:
                return self.say("I see "+str(counter)+" people.")
            
                    
        return { "error": False, "message": "OK" }
    
    def stop(self):
        return True
    
def create_skill():
    return WhoISeeSkill()