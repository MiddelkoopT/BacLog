#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import ConfigParser as configparser

## Use which data store.  [Database.driver stores value; not implemented]
#import postgres as database
import console as database

import packet
import bacnet

#### Main Class

class BacLog:
    def __init__(self):
        
        ## Configure
        self.config=configparser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        
        ## Load database driver
        self.db=database.Database()
        print "BacLog>", self.config.get('Network','bind'), self.db.database
        
        ## Work queues
        self.work={} # send/recv pair by invokeid
        self.done=[] # work finished
        self.data=[] # controller initiated data (wait++ to expect).
        
        ## Communication queues/expect
        self.send=[] # request queue
        self.wait=0  # wait for n packets
        
        self.invoke=0  # simple incrementing counter

        ## Bind
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind((self.config.get('Network','bind'),self.config.getint('Network','port')))
        self.socket.setblocking(0)
        
    def shutdown(self):
        print "BacLog> shutdown"
        self.socket.close()
        print "BacLog> exit"
        exit()

    def run(self):
        ## Read from database
        devices=self.db.getDevices();
        print "BacLog.run>", devices
        
        ## Test packet generation
        request=bacnet.ReadProperty('binary-output',20,'presentValue')
        self.addWork(request, devices[0][0])

        ## subscribe to COV for 2 min.
        subscribe=bacnet.SubscribeCOV()
        subscribe.pid=1
        subscribe.object=bacnet.ObjectIdentifier('binary-output',20)
        subscribe.confirmed=False
        subscribe.lifetime=120
        self.addWork(subscribe, devices[0][0])
        
        for target,instance in devices:
            readproperty=bacnet.ReadProperty('device',instance,'objectList')
            self.addWork(readproperty,target)

        self.process()
        for request,response,target in self.done:
            print "BacLog.run>", response, response.value
        self.shutdown()

        ## Depreciated
        
        
    def addWork(self,request,target):
        self.invoke+=1
        self.work[self.invoke]=(request,target)
        self.send.append((request,target,self.invoke))
        return self.invoke

    def process(self):
        ## Loop
        while(self.work or self.wait):
            print "BacLog.process> select:",
            s=self.socket
            if self.send:
                (sr,sw,se) = select.select([s],[s],[s])
            else:
                (sr,sw,se) = select.select([s],[],[s])
            print sr,sw,se
            ## Send
            if sw and self.send:
                (request,destination,invoke)=self.send.pop()
                p=packet.PDU[request._pdutype]()
                p.invoke=invoke
                p.servicechoice=request._servicechoice
                print "BacLog.process> send:", destination, invoke, p._display(request)
                s.sendto(p._encode(request),destination)
            ## Recv
            if sr:
                (recv,source)=s.recvfrom(1500)
                ## Process BVLC/NPDU and start of APDU
                p=packet.Packet(data=recv)
                print "BacLog.process> recv:", source, p.pdutype, binascii.b2a_hex(recv)
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
                    response=bacnet.UnconfirmedServiceChoice[p.servicechoice](data=p)
                    p=None
                if p and self.work.has_key(p.invoke):
                    # remove from work queue and put on done
                    request,target=self.work[p.invoke]
                    del self.work[p.invoke]
                    self.done.append((request,response,target))
                else:
                    # not work so put on data queue
                    self.data.append((p,source))
            ## Error
            if se:
                print "BacLog.process> error", se
                self.shutdown()

if __name__=='__main__':
    main=BacLog()
    main.run()
