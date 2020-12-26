'''
Project Karen: Synthetic Human
Created on Jul 20, 2020

@author: lnxusr1
@license: MIT License
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
        self.register_intent_file("cansee.intent", self.handle_seeme_intent)
        
        self.people = []
        try:
            self.people = json.loads(self.getContentsFromVocabFile("people.json"))
        except Exception as e:
            print(e)
            pass
    
    def handle_response1(self, message):
        #print(message)
        if message == "yes":
            return self.say("Then yes, I see you.")
        else:
            return self.say("Then no, I do not see you.")
    
    def handle_seeme_intent(self, message):
        if message.conf == 1.0:
            #print(message)
            data = self.getDataFromBrain("watcher_data")
            t = time.time()
            counter = 0
            person = None
            
            looking_for = ""
            if "me" in message.sent:
                looking_for = "me"
            elif "us" in message.sent:
                looking_for = "us"
            
            l = len(data)
            if l > 0:
                for z in data:
                    if z["lastFrame"] == True and z["last_seen"] > (t - 5):
                        counter = counter + 1
                        person = z
            
            if counter == 0:
                return self.say("No, I do not.") 
            
            if counter == 1:
                if looking_for == "me":
                    bFound = False
                    for item in self.people:
                        if item["id"] == person["idx"]:
                            t_name = item["name"]
                            if "spoken" in item:
                                t_name = item["spoken"]
                            
                            return self.ask("I'm not sure.  Are you " + str(t_name) + "?", self.handle_response1, timeout=10)
                            bFound = True
                            
                    if bFound == False:
                        return self.say("I see someone, but I'm not sure who it is.")
                else:
                    return self.say("No.  I see only one person and your question was plural.")
            
            if counter > 1:
                if looking_for == "us":
                    return self.say("Yes, I see all of you.")
            
        return { "error": True, "message": "Intent not understood" }

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