import unittest
import karen
import time 
    
class ListenerTests(unittest.TestCase):
    def test_startup(self):
        listener = karen.Listener()
        listener.start()
        listener.wait(5)
        self.assertTrue(listener.start())