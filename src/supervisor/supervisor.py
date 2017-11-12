import __main__ 
from ast import literal_eval
import traceback
import sys
import network
from network import Packet
import socket
from time import sleep
import io
import numpy as np
import json
import random
import numpy as np
from worker import _DEBUG_LEVEL
from multiprocessing import Queue
from queue import Empty



warden = None

networkmap = {} # wid: addr
aliases = {} # alias: wid
nethandler = None
workerpools = {} 
wardentags  = {}
scriptdepth = 0
packetQueue = Queue()

class ScriptFatalError(BaseException):
    pass

class Warden:
    '''
    Represents a Worker connected to this Supervisor
    Warden can be sent a job, a stream redirection info
    Workers are managed by a Warden
    You can get a Warden's stats, address,  
    '''
    
    def __init__(self):
        self.connection = None
        self.wid = None
        
    def requestStats(self):
        pck = Packet()
        pck.setType(network.PACKET_TYPE_WARDEN_STATS)
        self.connection.send(pck)
    
    def startWP(self, name, jobName, maxWorkers = 8, workerAmount = 0):
        pck = Packet()
        pck.setType(network.PACKET_TYPE_WORKER_POOL_CONFIG)
        '''
        id = data["id"]
        mw = int(data["maxWorkers"])
        wa = int(data["workerAmount"])
        jb = str(data["jobName"])
        '''
        
        pck["action"] = "create"
        pck["id"] = name
        pck["maxWorkers"] = maxWorkers
        pck["workerAmount"] = workerAmount
        pck["jobName"] = jobName
        
        self.connection.send(pck)
        
    def plugWP(self, sourceWP, remoteWarden, targetWP):
        pck = Packet()
        pck.setType(network.PACKET_TYPE_PLUG_REQUEST)
        '''
        data["sourceWP"] #the id of the local worker
        data["destinationWP"] #the id of the destination worker, remote or local
        data["remoteWarden"] #the warden holding the workerpool
        '''
        
        pck["sourceWP"] = sourceWP
        pck["destinationWP"] = targetWP
        pck["remoteWarden"] = remoteWarden
        
        self.connection.send(pck)
    
    def feedData(self, wpid, data):
        pck = Packet()
        pck.setType(network.PACKET_TYPE_DATA)
        pck["data"] = data
        pck["target"] = wpid
        
        self.connection.send(pck)
    
def purgeNetworkQueue():
    global packetQueue
    
    try:
        while True:
            packetQueue.get_nowait()
    except Empty:
        pass    

def holdForPacket(n=1):
    global packetQueue
    
    #purgeNetworkQueue()
    print("waiting for "+str(n))
    for i in range(n):
        packetQueue.get(True)
    print("resuming")
    
def notifyPacketReception():
    global packetQueue
    packetQueue.put('', True)
    
def network_connection_closed(data, conn = None):
    pass    

def network_connect_open(data, conn = None):
    pass
    
def network_auth(data, conn = None):
    global warden
    global wardentags
    
    wid = str(data["id"])
    print("[SUPERVISOR] WID is "+wid)
    warden.wid = wid
    
def network_plug_answer(data, conn = None):
    global workerpools
    global warden
    
    if(data["status"] == "OK"):
        warden.requestStats()
    else:
        print("Could not plug Worker pool: "+str(data["status"]))
        
    return

def network_warden_stats(data, conn = None):
    global networkmap
    global wardentags
    global workerpools
    
    wid = data["name"]
    
    wp = json.loads(data["wp"])["self"]
    for w in wp:
        workerpools[w] = wid # if a workerpool with this name already exists it is rewritten
                             # care should be taken in the script files
                             
    wa = json.loads(data["warden"])
    networkmap.clear()
    networkmap[wid] = "self"
    for w in wa:
        networkmap[w] = literal_eval(wa[w])[0]
    
    wt = json.loads(data["tags"])
    for tag in wt:
        if(not tag in wardentags):
            wardentags[tag] = []
        
        if(wid not in wardentags[tag]):
            wardentags[tag].append(wid)
    return

def network_wp_status(data, conn = None):
    global workerpools
    global warden
    
    if(data["status"] == "OK"):
        warden.requestStats()
    else:
        print("Could not set up Worker pool: "+str(data["status"]))
        
    return
    
def supervisorNetworkCallback(nature, data, conn = None):
    global _DEBUG_LEVEL
    
    if(_DEBUG_LEVEL == 3):
        print(str(nature)+ " "+ str(data) +" "+str(conn))
    
    if(nature == network.NATURE_ERROR):
        return True
    
    try:
        a = getattr(__main__, "network_"+str(nature))
        a(data, conn)
        
        if(not nature in network.CONNECTION_CONTROL):
            notifyPacketReception()
    except AttributeError:
        print("NO SUCH NETWORK METHOD "+nature)
        traceback.print_exc()    
    except BaseException:
        traceback.print_exc()
        
    
    
def execScript(path):
    try:
        f = open(path, "r")
    except FileNotFoundError:
        print("Script file not found: "+str(path))
        return
    
    for line in f:
        try:
            line = line.strip()
            print("> "+str(line))
            execReq(line)
        except ScriptFatalError as fe:
            print("Fatal Error occured, the script cannot continue")
            return
        except BaseException as e:
            traceback.print_exc()
            print("Error @: "+line)

def cycle_through(wlist):
    global warden
    
    for wid in wlist:
        if(wid != None and wid != warden.wid):
            return wid
    
    return None

def cmd_cc(tag = "", alias = None, crit = False): # Cycle Connection (connect to a warden with the given tag)
    global networkmap
    global wardentags
    global networkmap
    
    if(warden == None):
        print("Can't call this before connecting to a warden")
        return
    
    if(len(networkmap) == 0):
        return
    
    if(tag in wardentags):
        l = wardentags[tag]
    else:
        l = networkmap.keys()
        
    wid = cycle_through(l)
    if(wid != None):
        cmd_connect(wid, alias)
        return
        
    print("[SUPERVISOR] No suitable warden found")
    if(crit):
        raise ScriptFatalError()
    
    return 

def cmd_connect(addr="127.0.0.1", alias=None):
    global nethandler
    global aliases
    global networkmap
    global warden
    
    if(addr in networkmap and networkmap[addr] == "self"): #we are already connected to this warden
            return
    
    if(warden != None):
        cmd_disconnect()
    
    if(addr in aliases):
        addr = aliases[addr]
        print("[SUPERVISOR] Resolved alias name to "+str(addr))
        
    if(addr in networkmap):       
        wid = addr
        addr = networkmap[addr]
        print("[SUPERVISOR] Warden name "+str(wid)+" resolved to "+str(addr))
        
    print("[SUPERVISOR] Connecting to: "+str(addr))
    try:
        warden = Warden()
        c = nethandler.connect(addr)
        warden.connection = c
        holdForPacket()
    except:
        raise ScriptFatalError()
    
    warden.requestStats()
    holdForPacket()
    if(alias != None):
        aliases[alias] = addr
    print("[SUPERVISOR] Connected")
    
def cmd_winfo():
    global warden
     
    if(warden != None):
        print("Current warden is : "+str(warden.wid))
    else:
        print("No warden connected")


def cmd_call(script):
    global scriptdepth
    scriptdepth += 1
    if(scriptdepth > 7):
        print("Max script depth reached", file = sys.stderr)
        return
    
    execScript(script)
    scriptdepth -= 1
    
def cmd_exit():
    exit(0)

def cmd_plug(sourceWP, targetWP, targetWarden = None):
    global workerpools
    global warden

    if(sourceWP in workerpools and sourceWP != warden.wid):
        cmd_connect(workerpools[sourceWP])
    
    if(targetWP in workerpools and targetWarden == None):
        targetWarden = workerpools[targetWP]
        print("Warden for WP "+targetWP+" is "+targetWarden)
    
    warden.plugWP(sourceWP, targetWarden, targetWP)
    holdForPacket(2)

def cmd_explore():
    '''
    explore the network and collects the tags
    '''
    global networkmap
    global warden
    
    if(warden == None):
        print("Cannot exec explore before connecting to a warden")
        return
    
    if(len(networkmap) == 0):
        return
    
    store = warden.wid
    
    explored = []
    
    for wid in networkmap:
        if(wid in explored):
            continue
        
        cmd_printdebug()
        cmd_connect(wid)
        explored.append(wid)
    
    cmd_connect(store)
   
def cmd_printdebug():
    global networkmap
    global wardentags
    global packetQueue
    global workerpools
    
    print(str(networkmap))
    print(str(workerpools))
    print(str(wardentags))
    print(str(packetQueue.qsize()))

def cmd_stats():
    warden.requestStats()
    holdForPacket()
    
def cmd_stop():
    warden.stop()
    
def cmd_cwp(name, jobName, maxWorkers = 8, workerAmount = 0): # Create Worker Pool
    warden.startWP(name, jobName, maxWorkers, workerAmount)
    holdForPacket(2)
    
def cmd_disconnect():
    global warden
    
    if(warden != None):
        warden.connection.close()
    
    warden = None
    
def cmd_cae(addr="127.0.0.1", alias="local"): # Connect And Explore
    cmd_connect(addr, alias)
    cmd_explore()
    
def cmd_data(wpName, *args):
    global warden
    global workerpools
    
    if(not wpName in workerpools):
        print("Warden not found, create a WP before passing data to it")

    if(wpName in workerpools):    
        wid = workerpools[wpName] 
        if(wid != warden.wid):
            cmd_connect(wid)
        
    data = ""
    for i in args:
        data += i+" "
    warden.feedData(wpName, data)
    
def cmd_slapthedev():
    print("SPANK SPANK! Make something that works! (°...° )")
  
def cmd_testbin():
    global warden

    arr = np.random.randint(0, 255, size=(1280,1024,3))
    print(str(arr))
    p = network.createImagePacket(arr)
    warden.connection.send(p)

def execReq(cmd):
    global warden
    if(cmd == None or cmd.strip() == ""):
        return
    c = cmd.split(" ")
    a = getattr(__main__, "cmd_"+c[0])
    a(*c[1:])
    
        
def handleCommand(cmd):
    try:
        execReq(cmd.strip())
    except ScriptFatalError as e :
        raise e
    except BaseException:
        traceback.print_exc()
        print("Error in command", file = sys.stderr)


if(__name__ == "__main__"):
    print("============================")
    print("Tid'zam Camera SUPERVISOR")
    print("============================")
    
    nethandler = network.NetworkHandler(network.OBJECT_TYPE_SUPERVISOR, "supervisor", supervisorNetworkCallback, )
    while True:
        inp = input(">>> ")
        handleCommand(inp)
        
        
        