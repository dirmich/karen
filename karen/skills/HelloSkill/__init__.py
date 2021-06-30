from karen import Skill
import logging 

class HelloSkill(Skill):
    """
    Skill to say "Hello"
    """
    
    def __init__(self):
        """
        Hello Skill Initialization
        """
        
        self._name = "HelloSkill"
        self.logger = logging.getLogger("SKILL")
        self.logger.debug(self._name + "loaded successfully.")
    
    def initialize(self):
        """
        Load intent files for Hello Skill
        
        Returns:
            (bool): True on success else raises an exception
        """

        self.register_intent_file("hello.intent", self.handle_hello_intent)
        return True
        
    def handle_help_response(self, message, context=None):
        """
        Target callback for helper response
        
        Args:
            message (str): text of response (result of ask call).
            context (KContext): Context surrounding the request. (optional)
            
        Returns:
            (bool): True on success or False on failure
        """
        
        return self.say("GOT IT")

    def handle_hello_intent(self, message, context=None):
        """
        Primary function for intent matches.  Called by skill manager.
        
        Args:
            message (obj):  text that triggered the intent
            context (KContext): Context surrounding the request. (optional)
            
        Returns:
            (bool): True on success or False on failure
        """
        
        if message.conf == 1.0:
            
            if "help" in message.sent:
                return self.ask("How can I assist you?", self.handle_help_response)
            else:
                text = self.getMessageFromDialog("hello.dialog")
                if (text != "") and (text.lower() != "good night"):
                    return self.say(text)
                else:
                    return self.say("Hello")
        
        return False
    
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
        (object): HelloSkill instantiated class object
    """
    
    return HelloSkill()
