## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## BACnet UDP Message Driver

import socket
import binascii

import packet
import bacnet
import scheduler

debug=False
trace=False

class Message:
    _handler=None
    def __init__(self,remote,message=None,wait=True):
        self.remote=remote
        self.message=message
        self.wait=wait

    def __str__(self):
        return "[[%s:%s]]" % (self.remote,self.message)

class MessageHandler:
    """IO handler for scheduler class"""
    def __init__(self, address, port):
        if debug: print "MessageHandler>", address, port
        self.send=[]
        self.recv=[]
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((address,port))
        self.socket.setblocking(0)
        self.invoke=0
        self.wait={}
        self.service=[[None]*16]*8  ## Service Table
        Message._handler=self
        
        
    def addService(self,task,service):
        print "MessageHandler.addService>", service._servicechoice, service
        self.service[service._pdutype][service._servicechoice]=task
        
    ## Handler API
        
    def put(self,work):
        invoke=self.invoke+1
        request=work.request.message
        remote=work.request.remote
        p=packet.PDU[request._pdutype]()
        p.invoke=invoke
        p.servicechoice=request._servicechoice
        if debug: print "MessageHandler.put>", remote, invoke, p._display(request)
        self.invoke=invoke
        self.wait[invoke]=work.tid
        self.send.append((remote,p._encode(request)))
        
    def writing(self):
        return len(self.send) > 0
    
    def reading(self):
        return True
        
    def write(self):
        remote,data=self.send.pop(0)
        sent=self.socket.sendto(data, remote)
        assert sent==len(data) ## Send entire packet.
        if trace: print "MessageHandler.write>", remote
        
    def read(self):
        (recv,remote)=self.socket.recvfrom(1500)
        self.recv.append((recv,remote))
        if trace: print "MessageHandler.read>", remote
        
    def get(self):
        recv,remote=self.recv.pop(0)
        ## Process BVLC/NPDU and start of APDU
        p=packet.Packet(data=recv)
        if trace: print "MessageHandler.get>", remote, p.pdutype, binascii.b2a_hex(recv)
        ## Process PDU
        p=packet.PDU[p.pdutype](data=recv)
        message=None
        tid=None
        if(p.pdutype==0x3): ## ComplexACK
            message=bacnet.ConfirmedServiceResponseChoice[p.servicechoice](data=p)
            tid=self.wait[p.invoke]
        elif p.pdutype==0x2: ## SimpleACK
            message=bacnet.Boolean(True)
            tid=self.wait[p.invoke]
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

        work=scheduler.Work(tid)
        work.response=Message(remote,message)
        return work
    
    def shutdown(self):
        self.socket.close()
