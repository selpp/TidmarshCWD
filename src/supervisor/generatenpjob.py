'''
Created on 7 nov. 2017

@author: WIN32GG
'''

from worker import Job
import numpy as np

class generatenpjob(Job):
    
    def setup(self):
        self.a = 0
    
    def loop(self, data):
        self.a += 1
        
        if(self.a > 100):
            self.shouldExit = True
            return None
        
        return ( {"a": "issou"}, np.random.randint(0, 255, size = (1280, 1080, 3)))
    
    
    def requireData(self):
        return False