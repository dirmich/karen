'''
Project Karen: Synthetic Human
Created on July 12, 2020
@author: lnxusr1
@license: MIT License
@summary: Skill and Skill Manager classes for learned skills
'''

import os, logging, random
from padatious import IntentContainer
from .shared import dayPart

class SkillManager:
    """Translates text commands into skill results."""
    
    def __init__(self, brain_obj=None):
        self.logger = logging.getLogger("SKILLMANAGER")
        self.skill_folder = ""
        self.brain = brain_obj
        
        self.skills = []

    def initialize(self):
        
        self.logger.debug("Initalizing")
        
        self.intentParser = IntentContainer('/tmp/intent_cache')

        d = os.path.join(os.path.dirname(__file__), "skills")
        skillModules = [os.path.join(d, o) for o in os.listdir(d) 
                    if os.path.isdir(os.path.join(d,o))]
        
        for f in skillModules:
            mySkillName = os.path.basename(f)
            self.logger.debug("Loading " + mySkillName) 
            mySkillModule = __import__(mySkillName)
            mySkillClass = mySkillModule.create_skill()
            mySkillClass.brain = self.brain
            mySkillClass.initialize()
            
        #print(self.skills)
        self.logger.debug("Skills load is complete.")
        
        self.intentParser.train(False) # False = be quiet and don't print messages to stdout

        self.logger.debug("Training completed.")

        self.logger.debug("Initialization completed.")

        
    def parseInput(self, text):

        def audioFallback(in_text):
            
            if "thanks" in in_text or "thank you" in in_text:
                if self.brain is not None:
                    res = self.brain.say("You're welcome.")
                    if res["error"] == False:
                        return { "error": False, "message": "Skill completed successfully." }
                
            # Some simple responses to important questions
            elif "who are you" in in_text or "who are u" in in_text:
                res = self.brain.say("I am a synthetic human.  You may call me Karen.")
                if res["error"] == False:
                    return { "error": False, "message": "Skill completed successfully." }
            elif "how are you" in in_text:
                res = self.brain.say("I am online and functioning properly.")
                if res["error"] == False:
                    return { "error": False, "message": "Skill completed successfully." }
            elif "you real" in in_text and len(in_text) <= 15:
                res = self.brain.say("What is real?  If you define real as electrical impulses flowing through your brain then yes, I am real.")
                if res["error"] == False:
                    return { "error": False, "message": "Skill completed successfully." }
            elif "you human" in in_text and len(in_text) <= 17:
                res = self.brain.say("More or less.  My maker says that I am a synthetic human.")
                if res["error"] == False:
                    return { "error": False, "message": "Skill completed successfully." }
            elif "is your maker" in in_text and len(in_text) <= 20:
                res = self.brain.say("I was designed by lnx user  one in 2020 during the Covid 19 lockdown.")
                if res["error"] == False:
                    return { "error": False, "message": "Skill completed successfully." }
                                        
            self.logger.debug("fallback: " + in_text)
            return { "error": True, "message": "Intent not understood." }

        try:
            intent = self.intentParser.calc_intent(text)
            #print(intent)
            # I need to be at least 60% likely to be correct before I try to process the request.
            if intent.conf >= 0.6:
                for s in self.skills:
                    if intent.name == s["intent_file"]:
                        #TODO: What happens if we get an incorrect intent determination?
                        ret_val = s["callback"](intent)
                        try:
                            if ret_val["error"] == True:
                                return audioFallback(text)
                            else:
                                return { "error": False, "message": "Skill completed successfully." }
                        except:
                            # Should we just assume it completed successfully?
                            return { "error": False, "message": "Skill completed successfully." }
            else:
                return audioFallback(text)
        except Exception as e:
            self.logger.debug(str(e))
            return { "error": True, "message": "Error occurred in processing." }

        return { "error": True, "message": "Unable to process input."}
    
    def stop(self):
        if (self.skills is not None and len(self.skills) > 0):
            for s in self.skills:
                try:
                    s["object"].stop()
                except:
                    pass

        return True
    
class Skill:
        
    def __init__(self):
        self._name = "Learned Skill"
        self.brain = None 
    
    def ask(self, in_text, in_callback, timeout=0):
        
        if self.brain is not None:
            return self.brain.ask(in_text, in_callback, timeout=timeout)
        else:
            self.logger.debug("BRAIN not referenced")

        return { "error": True, "message": "Error in Ask command" }
    
    def getMessageFromDialog(self, dialog_file, **args):
        text = ""
        df = os.path.join(os.path.dirname(__file__), "skills", self.__class__.__name__, "vocab", "en_us", dialog_file)
        
        if os.path.exists(df):
            with open(df,"r") as s:
                m=s.readlines()
                l=[]
                for i in range(0,len(m)-1):
                    x=m[i]
                    z=len(x)
                    a=x[:z-1]
                    l.append(a)
                l.append(m[i+1])
                text=random.choice(l)
                    
            if ("*dayPart*" in text):
                text = text.replace("*dayPart*", dayPart())
            
            return text
        else:
            return ""
        
    def getContentsFromVocabFile(self, filename):
        filename = os.path.join(os.path.dirname(__file__), "skills", self.__class__.__name__, "vocab", "en_us", filename)
        if os.path.exists(filename):
            with open(filename, "r") as f:
                text = f.read()
                
            return text
        else:
            return ""
        
    #def getDataFromBrain(self, x_type="watcher_data"):
    #    if x_type != "":
    #        return self.brain.getFileData(str(x_type).lower()+".json")
    #    else:
    #        return []

    def initialize(self):
        return True
        
    def register_intent_file(self, filename, callback):
        fldr = os.path.join(os.path.dirname(__file__), "skills", self.__class__.__name__)
        if os.path.exists(fldr):
            if os.path.exists(fldr):
                if self.brain is not None:
                    self.brain.skill_manager.intentParser.load_file(filename, os.path.join(fldr,"vocab","en_us",filename), reload_cache=True)
                    self.brain.skill_manager.skills.append({ "intent_file": filename, "callback": callback, "object": self })
                else:
                    self.logger.debug("BRAIN not referenced")
            else:
                self.logger.debug("Error registering intent file")
        else:
            self.logger.debug("Intent file not found")
            return False
        
        return True
    
    def say(self, in_text):
        
        if self.brain is not None:
            return self.brain.say(in_text)
        else:
            self.logger.debug("BRAIN not referenced")

        return { "error": True, "message": "Error in Say command" }

    def stop(self):
        return True