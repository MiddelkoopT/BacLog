#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Main I/O and Task scheduler

import select
import socket
import binascii

import packet
import bacnet

class Task:
    tid=0
    def __init__(self):
        Task.tid+=1
        self.tid=Task.tid
        self.send=self.run().send

class Work:
    def __init__(self,tid,request=None):
        self.tid=tid
        self.request=request
        self.response=None

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
        elif p.pdutype==0x2: ## SimpleACK
            p=packet.SimpleACK(data=recv)
            response=bacnet.Boolean(True)
            response.value=response._value
        elif p.pdutype==0x1: ## Unconfirmed Request
            p=packet.UnconfirmedRequest(data=recv)
            service=bacnet.UnconfirmedServiceChoice.get(p.servicechoice,None)
            response=service and service(data=p)
        
        if not response:
            return False ## discarded data.
        work=Work(p.invoke)
        work.response=Message(remote,response)
        return work
    
    def shutdown(self):
        self.socket.close()

class Scheduler:
    def __init__(self):
        print "Scheduler>"
        self.task={}
        self.work=[]
        self.done=[]
        
        self.handler=[]
        self.socket={}
    
    def addHandler(self,handler):
        self.handler.append(handler)
        self.socket[handler.socket]=handler
            
    def add(self,task):
        assert isinstance(task, Task)
        self.task[task.tid]=task
        self.done.append(Work(task.tid)) ## Prime
        
    def run(self):
        print "Scheduler.run> start"
        while self.task:
            block=5 ## start off with blocking.
            if self.done: 
                block=0
            while True:
                print "Scheduler.run> select"
                r,w,x=[],[],[]
                for h in self.handler:
                    r.append(h.socket)
                    h.send and w.append(h.socket)
                    x.append(h.socket)
                (sr,sw,sx) = select.select(r,w,x,block)
                assert not sx

                ## Nothing to do.
                if (not sr) and (not sw) and (not sx):
                    print "Scheduler.run> empty"
                    break

                block=0 ## Data exists

                ## Send
                for s in sw:
                    print "Scheduler.run> write"
                    handler=self.socket[s]
                    handler.write()
    
                ## Recv
                for s in sr:
                    print "Scheduler.run> read"
                    handler=self.socket[s]
                    handler.read()
            
            ## Pair responses
            for h in self.handler:
                while h.recv:
                    work=h.get()  ## Handlers do the paring.
                    self.done.append(work)
                    print "Scheduler.run> pair", work
            
            ## Deliver responses to tasks and collect new messages.
            while self.done:
                try:
                    work=self.done.pop(0)
                    task=self.task[work.tid]
                    print "Scheduler.run> done", work.tid, work.response
                    send=task.send(work.response) ## Main coroutine entry point
                    print "Scheduler.run> work", send
                    send._handler.put(Work(work.tid,send))
                except StopIteration:
                    print "Scheduler.run> %d exited" % work.tid
                    del self.task[work.tid]
                    continue

        print "Scheduler.run> done", self.work, self.done
        assert not self.work and not self.done
        
    def shutdown(self):
        Message._handler.shutdown()

