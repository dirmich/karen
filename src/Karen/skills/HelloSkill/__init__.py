from Karen import Skill 
import logging 

class HelloSkill(Skill):
    def __init__(self):
        self._name = "HelloSkill"
        logging.debug("SKILL - " + self._name + "loaded successfully.")
    
    def initialize(self):
        self.register_intent_file("hello.intent", self.handle_hello_intent)
        

    def handle_hello_intent(self, message):
        if message.conf == 1.0:
            #print(message)
            
            if "help" in message.sent:
                return self.say("How can I assist you?")
            else:
                text = self.getMessageFromDialog("hello.dialog")
                if (text != "") and (text.lower() != "good night"):
                    return self.say(text)
                else:
                    return self.say("Hello")
        
        return { "error": False, "message": "OK" }
    
    def stop(self):
        return True
    
def create_skill():
    return HelloSkill()