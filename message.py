## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## BACnet UDP Message Driver

import socket
import binascii

import packet
import bacnet
import scheduler

class Message:
    _handler=None
    def __init__(self,remote,message=None,wait=True):
        self.remote=remote
        self.message=message
        self.wait=wait

    def __str__(self):
        return "[[%s:%s]]" % (self.remote,self.message)

class MessageHandler:
    def __init__(self, address, port):
        print "MessageHandler>", address, port
        self.send=[]
        self.recv=[]
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((address,port))
        self.socket.setblocking(0)
        Message._handler=self
        
    def put(self,work):
        invoke=work.tid
        request=work.request.message
        remote=work.request.remote

        p=packet.PDU[request._pdutype]()
        p.invoke=invoke
        p.servicechoice=request._servicechoice
        print "MessageHandler.put>", remote, invoke, p._display(request)
        self.send.append((remote,p._encode(request)))
        
    def write(self):
        remote,data=self.send.pop(0)
        sent=self.socket.sendto(data, remote)
        assert sent==len(data) ## Send entire packet.
        print "MessageHandler.write>", remote
        
    def read(self):
        (recv,remote)=self.socket.recvfrom(1500)
        self.recv.append((recv,remote))
        print "MessageHandler.read>", remote
        
    def get(self):
        recv,remote=self.recv.pop(0)
        ## Process BVLC/NPDU and start of APDU
        p=packet.Packet(data=recv)
        print "MessageHandler.get>", remote, p.pdutype, binascii.b2a_hex(recv)
        ## Process PDU
        if(p.pdutype==0x3): ## ComplexACK
            p=packet.ComplexACK(data=recv) # Parse PDU
            response=bacnet.ConfirmedServiceResponseChoice[p.servicechoice](data=p)
            tid=p.invoke
        elif p.pdutype==0x2: ## SimpleACK
            p=packet.SimpleACK(data=recv)
            response=bacnet.Boolean(True)
            tid=p.invoke
        elif p.pdutype==0x1: ## Unconfirmed Request
            p=packet.UnconfirmedRequest(data=recv)
            service=bacnet.UnconfirmedServiceChoice.get(p.servicechoice,None)
            response=service and service(data=p)
            print response
            tid=response.pid._value

        assert response ## Discarded data        
        if not response:
            return False 

        work=scheduler.Work(tid)
        work.response=Message(remote,response)
        return work
    
    def shutdown(self):
        self.socket.close()

