'''

@author: WIN32GG
'''

import sys
import traceback
import os.path

"""
    DEBUG OUTPUT HANDLING
"""
#debug level 0,1,2,3 the higher, the depper debug
_DEBUG_LEVEL = 3 #FIXME not sensible to change
_DEBUG_DICT  = {0:"Minimum", 1: "Supervisor info", 2: "Workers status", 3: "Everything (debug)"}

class Profiler():

    
    def __init__(self):
        self.position = []
        
    def enter(self, sectionName):
        self.position[len(self.position - 1)] = sectionName
        
    def exit(self, sectionName = None):
        try:
            if(sectionName == None):
                del self.position[len(self.position) -1]
            else:
                del self.position[self.position.index(sectionName):]
        except:
            pass
        
    def add(self, sectionName):
        self.position.append(sectionName)
         
    def exitAll(self):
        self.position = []
    
    def getText(self):
        txt = "("
        for e in self.position:
            txt += "->"+e
            
        return txt+") "
    
    
    
def _getTB():
    tb = traceback.extract_stack()
    s = tb[len(tb) -3]
    #traceback.print_stack()
    #print(str(traceback.extract_stack()))
    name = "line n°"+str(s.lineno) if s.name == '<module>' else s.name 
    return "("+os.path.basename(s.filename)+" > "+name+") "

def debug(msg, level = 1, err= False):
    stream = sys.stderr if err else sys.stdout
    sts = "[INFO] [LV "+str(level)+"] " if level < 3 else "[DEBUG] "
    prf = _getTB()#profiler.getText()
    sts += prf
    msg = "[ERROR] "+prf+msg if err else sts + msg
    
    if(level <= _DEBUG_LEVEL):
        stream.write(msg+"\n")
        stream.flush()
    

