## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## BACnet UDP Message Driver

import socket
import binascii
import time

import packet
import bacnet
import scheduler


debug=False
trace=False

class Message:
    _handler=None
    def __init__(self,remote,message=None,invoke=None,timeout=2.0):
        self.remote=remote
        self.message=message
        self.invoke=invoke
        if invoke!=None: ## Reply messages do not timeout.
            self.timeout=None
        else:
            self.timeout=timeout
        self.stamp=None

    def __repr__(self):
        return "[[%s:%s]]" % (self.remote,self.message)

class MessageHandler:
    """IO handler for scheduler class"""
    TIMEOUT=0.1
    def __init__(self, address, port):
        if debug: print "MessageHandler>", address, port
        self.send=[]
        self.recv=[]
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((address,port))
        self.socket.setblocking(0)
        self.invoke=0
        self.wait={}
        self.timeout={}
        self.sleep=0
        self.service=[[None]*16]*8  ## Service Table
        Message._handler=Message._handler or self
        
        
    def addService(self,task,service):
        if debug: print "MessageHandler.addService>", service._servicechoice, service
        self.service[service._pdutype][service._servicechoice]=task
        
    ## Handler API
        
    def put(self,work):
        request=work.request.message
        remote=work.request.remote
        timeout=work.request.timeout

        p=packet.PDU[request._pdutype]()
        p.servicechoice=request._servicechoice

        if work.request.invoke!=None: ## this is a reply/resend.
            p.invoke=work.request.invoke
        else:
            self.invoke=(self.invoke+1)%256 ## Increment counter
            if self.wait.has_key(self.invoke):
                if debug: print "MessageHandler.put> invoke search", self.invoke, self.wait 
                self.invoke=None
                for i in range(0,256):
                    if not self.wait.has_key(i):
                        self.invoke=i
                        break
                assert self.invoke!=None ## could not find empty slot
            work.request.invoke=p.invoke=self.invoke
            self.wait[p.invoke]=(work.tid,work)

        if timeout: ## timeout requested, no timeout on reply (invoke set) messages
            self.timeout[p.invoke]=self.time+timeout

        if debug: print "MessageHandler.put>", remote, p.invoke
        self.send.append((remote,p._encode(request)))
        
    def writing(self):
        return len(self.send) > 0
    
    def reading(self):
        return True
    
    def ready(self,time):
        self.time=time
        if not self.timeout:
            return False
        if time-self.sleep<0:
            return False
        self.sleep=time+self.TIMEOUT
        return True
    
    def process(self):
        for invoke,timeout in self.timeout.items():
            if self.time-timeout > 0:
                tid,work=self.wait[invoke]
                print "MessageHandler.process> timeout:", invoke, tid, work.request
                del self.timeout[invoke]
                self.put(work) ## resend
    
    def write(self):
        remote,data=self.send.pop(0)
        sent=self.socket.sendto(data, remote)
        assert sent==len(data) ## Send entire packet.
        if trace: print "MessageHandler.write>", remote
        
    def read(self):
        (recv,remote)=self.socket.recvfrom(1500)
        self.recv.append((recv,remote,time.time()))
        if trace: print "MessageHandler.read>", remote
        
    def get(self):
        recv,remote,stamp=self.recv.pop(0)
        ## Process BVLC/NPDU and start of APDU
        p=packet.Packet(data=recv)
        if trace: print "MessageHandler.get>", stamp, remote, p.pdutype, binascii.b2a_hex(recv)
        ## Process PDU
        p=packet.PDU[p.pdutype](data=recv)
        message=None
        tid=None
        work=None
        ## Response messages.
        if(p.pdutype==0x3): ## ComplexACK
            message=bacnet.ConfirmedServiceResponseChoice[p.servicechoice](data=p)
            tid,work=self.wait.pop(p.invoke) ## remove pending message from wait queue
            self.timeout.pop(p.invoke,None)  ## remove timeout
        elif p.pdutype==0x2: ## SimpleACK
            message=bacnet.Boolean(True)
            tid,work=self.wait.pop(p.invoke) ## remove pending message from wait queue
            self.timeout.pop(p.invoke,None)  ## remove timeout
        elif p.pdutype==0x5: ## Error
            message=bacnet.Error(data=p) ## service choice is ignored since most are "Error"
            tid,work=self.wait.pop(p.invoke) ## remove pending message from wait queue
            self.timeout.pop(p.invoke,None)  ## remove timeout
        ## Request messages
        else: ## Unconfirmed and Confirmed Request
            service=bacnet.ServiceChoice[p.pdutype].get(p.servicechoice,None)
            if not service:
                print "MessageHandler.get>", p.servicechoice, service
                return False
            message=service(data=p)
            task=self.service[p.pdutype][p.servicechoice]
            if task:
                tid=task.tid
                
            if hasattr(message,'pid'):
                tid=message.pid._value
                
            if tid==None:
                print "MessageHandler.get> Unknown handler", message
                return False

        if not message:
            print "MessageHandler.get> Unknown packet", binascii.b2a_hex(recv)
            return False        
        
        work=work or scheduler.Work(tid)
        work.response=Message(remote,message,getattr(p,'invoke',None))
        work.response.stamp=stamp
        return work
    
    def shutdown(self):
        self.socket.close()
