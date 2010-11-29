#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import ConfigParser

# Use which data store.  [Database.driver stores value; not implemented so pydev will follow]
#import postgres as database
import console as database

import packet
import bacnet

#### Main Class

class BacLog:
    def __init__(self):
        
        ## Configure
        self.config=ConfigParser.ConfigParser()
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
        print "BacLog.run>"

        ## Read from database
        devices=self.db.getDevices();
        target=devices[0]
        objects=self.db.getObjects(target)
        object=objects[0]
        print "BacLog.run>", target, objects
        
        ## Setup test packet for first object
        readproperty=bacnet.ReadProperty()
        readproperty.object=bacnet.ObjectIdentifier(*object)
        readproperty.property=bacnet.PropertyIdentifier('presentValue')
        request=packet.ConfirmedRequest(readproperty)

        self.work[request.pid]=(request,target)
        self.send.append((request,target))
        
        ## subscribe to COV for 2 min.
        subscribe=bacnet.SubscribeCOV()
        subscribe.pid=258
        subscribe.object=bacnet.ObjectIdentifier(*object)
        subscribe.confirmed=False
        subscribe.lifetime=120
        request=packet.ConfirmedRequest(subscribe)

        self.work[request.pid]=(request,target)
        self.send.append((request,target))
        
        self.process()
        for request,response,target in self.done:
            print "BacLog.run>", response.value
        self.shutdown()

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
                (request,destination)=self.send.pop()
                print "BacLog.process> send:", destination, request.pid, request
                s.sendto(request._encode(),destination)
            ## Recv
            if sr:
                (recv,source)=s.recvfrom(1500)
                ## Process BVLC/NPDU and start of APDU
                p=packet.Packet(data=recv)
                print "BacLog.process> recv:", source, p.pdutype, binascii.b2a_hex(recv)
                ## Process PDU
                if(p.pdutype==0x3): ## ComplexACK
                    p=packet.ComplexACK(data=recv) # Parse PDU
                    print "BacLog.process>", p.servicechoice 
                    response=bacnet.ConfirmedServiceResponseChoice[p.servicechoice](data=p)
                    print "DEBUG:",response.value
                elif p.pdutype==0x2: ## SimpleACK
                    p=packet.SimpleACK(data=recv)
                    response=bacnet.Boolean(True)
                    response.value=response._value
                elif p.pdutype==0x1: ## Unconfirmed Request
                    p=packet.UnconfirmedRequest(data=recv)
                    response=bacnet.UnconfirmedServiceChoice[p.servicechoice](data=p)
                    print "DEBUG:",response.values.presentValue.value
                    p=None
                if p and self.work.has_key(p.pid):
                    # remove from work queue and put on done
                    request,target=self.work[p.pid]
                    del self.work[p.pid]
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
