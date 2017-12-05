'''

@author: WIN32GG
'''
from time import sleep
import network

'''
Master file to control all supervisors
Receive the config for the cluster, checks it and run sends to supervisor
(V1.5: Also asks and get the supervisor status and can show it in a web application) 
'''

import json
import sys
import traceback
import re
import socket

import config_checker
from customlogging import _DEBUG_LEVEL
from customlogging import debug


class RemoteSupervisor:
    
    def __init__(self, name, addr):
        self.addr = addr
        self.name = name
        
    def _test(self, testConnect = True):
        if(not self._matchAdress()):
            raise ValueError("Invalid IP for unit "+self.name)
        
        if(self.addr[0] == "127.0.0.1"):
            raise ValueError("Cannot use loopback as an address")
        
        if(testConnect and not self._testConnection()):
            raise ValueError("Unreacheable Supervisor for unit "+self.name)
        
    def _testConnection(self):
        s = self._connect()
        if(s == None):
            return False
        
        self._close(s)
        return True
        
    def _close(self, sck):
        sck.shutdown(socket.SHUT_RDWR)
        sck.close()
        
    def _connect(self):
        try:
            
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.settimeout(2.5)
            sck.connect(self.addr)
            debug("Connected to "+str(self.addr))
            return sck
        except:
            if(_DEBUG_LEVEL >= 3):
                traceback.print_exc()
            return None
        
    def _matchAdress(self):
        return re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", self.addr[0]) != None
    
  
    def push(self, obj, throwOnError = True):
        debug("Pushing to "+self.name)
        sock = self._connect()
        chan = sock.makefile("rwb")
        
        network.sendString(chan, json.dumps(obj))
        debug("Awaiting reply...")
        answ = network.readString(chan) or "SOCK_TIMEOUT"
        
        try:
            self._close(sock)
        except:
            pass
        
        if(answ != network.OK):
            if(throwOnError):
                debug("Push failure", 0, True)
                debug("Refer to supervisor log for details", 0, True)
                debug("Err was:"+answ,0 ,True)
                return False
            
        debug("OK")
        return answ

def loadSupervisors(cfg):
    debug("Master config sanity check...")
    if(not config_checker.checkMasterConfigSanity(cfg)):
        return
    
    objCfg = json.loads(cfg)  
    
    debug("Loading Supervisors...")
    return loadUnits(objCfg['units'])        
        
 
        
def loadUnits(units):
    
    rsup = {}
    
    for u in units:
        name = u['name']
        debug("Testing RemoteSupervisor "+name, 2)
        if(name in rsup.keys()):
            raise ValueError("Worker name "+str(name)+" is already registred")

        rs = RemoteSupervisor(name, (u['address'], 55555)) #TODO port handling
        rs._test()
        rsup[name] = rs
        debug("Supervisor "+name+": OK", 2)

    return rsup

def checkWorkerConfig(cfg):
    return config_checker.checkWorkerConfigSanity(cfg)
       
def loadWorkerSequence(objCfg, rsup):
    debug("Creating worker sequence...")
    workerSequence, workerSup, workerByName = loadWorkerDistributionSequence(objCfg['workers'], rsup)
    
    return (workerSequence, workerSup, workerByName)

def loadWorkerDistributionSequence(workers, rsup):
    
    def buildWorkerSequence(seq, workerDict, currentWorker):
        if(currentWorker in seq):
            return
        
        if("output" in workerDict[currentWorker].keys()):
            output = workerDict[currentWorker]['output']
            for i in range(len(output)):
                out = output[i]
                buildWorkerSequence(seq, workerDict, out)
                
                trueOut = workerSuper[out].addr[0]+":"+str(workerDict[out]['port'])
                debug("Resolved "+out+" to "+trueOut)
                output[i] = trueOut
                
        seq.append(currentWorker)
    
    workerByName = {}
    workerSuper  = {}
    
    workerSequence = []
    
    for sup in workers.keys():
        if(not sup in rsup):
            raise ValueError("The requested unit is unknown: "+sup)
        
        for worker in workers[sup]:
            
            name = worker["workername"]
            
            debug("Loading: "+name)
            if(not checkWorkerConfig(json.dumps(worker))):
                raise ValueError("Unable to load config for worker: "+name)
            
            if(worker["workername"] in workerByName):
                raise ValueError("Duplicate for worker name "+name)
    
            workerByName[name] = worker
            workerSuper[name] = rsup[sup]

    debug("Got "+str(len(workerByName))+" workers and "+str(len(rsup))+" supervisors")
    
    try:
        for w in workerByName.keys():
            buildWorkerSequence(workerSequence, workerByName, w)
    except KeyError as e:
        debug("Unknown Worker: "+str(e), 0, True)
        raise e

    debug("Worker ignition sequence is "+str(workerSequence))
    return (workerSequence, workerSuper, workerByName)

def pushAction(objCfg, rSup):
    obj = {"action":objCfg['action']}
    answ = {}
    
    for sup in rSup.values():
        a = sup.push(obj, False)
        answ[sup.name] = a
    
    return json.dumps(answ)

def pushConfig(objCfg, rSup):
    workerSequence, workerSup, workerByName = loadWorkerSequence(objCfg, rSup)
    
    for name in workerSequence:
        w = workerByName[name]
        if(not workerSup[name].push(w)):
            break


def read(fil):
    fd = open(fil, "r")
    d = ""
    for k in fd:
        d += k.strip()
    fd.close()
    return d

################## MAIN

if __name__ == '__main__':
    debug("Starting Master...",0)
    cfg = None
    
    if(len(sys.argv) > 1):  
        debug("Using config file: "+str(sys.argv[1]))
        fil = sys.argv[1]
        cfg = read(fil)
        debug(cfg, 3)

    if(cfg == None):
        debug("Master started, awaiting config", 0)
        cfg = input().strip()
    
    debug("Reading config...")
    try:
        rSup = loadSupervisors(cfg)
        objCfg = json.loads(cfg)
        
        if("action" in objCfg.keys()):
            answ = pushAction(objCfg, rSup)
            print(answ)
        else:
            pushConfig(objCfg, rSup)
        
        
    except Exception as e:
        debug("An exception occured when executing the config", 0, True)
        debug(repr(e), 0, True)
        if(_DEBUG_LEVEL >= 3):
            traceback.print_exc()
    
    

