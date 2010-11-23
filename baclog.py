#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import ConfigParser

# Use which data store.  [Database.driver stores value; not implemented so pydev will follow]
#import postgres as database
import console as database

import bacnet

from depreciated import *
from packet import *
from tagged import *

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
        request=ReadPropertyRequest(*object)
        response=ReadPropertyResponse(request)

        ## Raw UDP data (debug)
        #request=RawPacket("")
        #response=ResponsePacket(None,None)
        
        self.work[request.pid]=(request,response,target)
        self.send.append((request,target))
        
        ## subscribe to COV for 2 min.
        subscribe=SubscribeCOVRequest(object)
        print subscribe
        subscribe=bacnet.SubscribeCOV()
        subscribe.pid=0
        subscribe.object=bacnet.ObjectIdentifier(*object)
        subscribe.confirmed=False
        subscribe.lifetime=120
        print binascii.b2a_hex(subscribe._encode())
                
        self.work[subscribe.pid]=(subscribe,SimpleACK(subscribe),target)
        self.send.append((subscribe,target))
        
        self.process()
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
                (response,source)=s.recvfrom(1500)
                ## Process BVLC/NPDU and start of APDU
                r=Packet(data=response)
                print "BacLog.process> recv:", source, r.pdutype, binascii.b2a_hex(response)
                ## Process PDU
                if(r.pdutype==0x3): ## ComplexACK
                    r=ComplexACK(data=response) # Parse PDU
                elif r.pdutype==0x2: ## SimpleACK
                    r=SimpleACK(data=response)
                elif r.pdutype==0x1: ## Unconfirmed Request
                    r=UnconfirmedRequest(data=response)
                    ## FIXME: Hard coded packet choice.
                    if r.servicechoice==BACnetUnconfirmedServiceChoice['unconfirmedCOVNotification']:
                        r=UnconfirmedRequest('unconfirmedCOVNotification',response)
                        d=bacnet.UnconfirmedCOVNotification(data=r)
                        print "DEBUG:",d.values.presentValue.value
                        r=None
                if r and self.work.has_key(r.pid):
                    # remove from work queue and put on done
                    self.work[r.pid][1]._decode(response)
                    self.done.append(self.work[r.pid])
                    del self.work[r.pid]
                else:
                    # not work so put on data queue
                    self.data.append((response,source))
            ## Error
            if se:
                print "BacLog.process> error", se
                self.shutdown()

if __name__=='__main__':
    main=BacLog()
    main.run()
