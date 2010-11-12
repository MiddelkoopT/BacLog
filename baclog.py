#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import struct
import string
import types
import ConfigParser

# Use which data store.  [Database.driver stores value; not implemented so pydev will follow]
#import postgres as database
import console as database

## Specification Enumerations
BACnetObjectType = {'binary-input':3,'binary-output':4, 'device':8}
BACnetPropertyIdentifier = {'present-value':85, 'object-list':76, 'notification-class':17}
BACnetConfirmedServiceChoice = {'readProperty':12, 'subscribeCOV':5 }

## Used to get a new request ID
LastRequestID = 0        

class RawPacket:
    """Test packet class (send raw hex encoded packet)"""
    def __init__(self,data=None,id=None):
        self.data=data
        self.id=id
        
    def __call__(self):
        return binascii.unhexlify(self.data)

class Packet:
    """Magic Packet Class (somewhat an abstract class)."""
    def __init__(self,control=None,pdu=None,data=None):
        self._field=[]      # (name,value) of variable (None for constant/default)
        self._format=[]     # format of the field
        self._tag=[0]       # current context tag
        
        ## BVLC
        self._add(None,'B',0x81)            # BACnet/IP
        self._add(None,'B',0x0a)            # UDP
        self._add('_length','H')            # Packet size
        ## NPDU
        self._add('version','B',0x01)       # ASHRAE 135-1995
        self._add('control','B',control)    # NPDU Control; Confirmed Request=0x04
        ## APDU header
        self._add('_pdu','B',pdu)           # (pdutype<<4 | pduflags)
        
        ## Unknown packets set data
        data and self(data)
        
        # Set computed fields.
        if(self._pdu!=None):
            self.pdutype=(self._pdu&0xF0) >> 4
            self.pduflags=(self._pdu&0x0F) 
        
    def _add(self,name,format,value=None):
        self._field.append((name,value))
        self._format.append(format)
        if name:
            setattr(self, name, value)
        
    def __str__(self):
        return "%s %d" % (binascii.b2a_hex(self()), self._length)

    def __call__(self, data=None):
        if(data==None):
            return self._encode()
        else:
            self._decode(data)
        
    def _encode(self):
        """Generate Packet Data"""
        packet=struct.Struct('!'+string.join(self._format))
        ## Generated fields
        self._length=packet.size
        self._pdu=self.pdutype<<4|self.pduflags 

        values=[]
        for (name,value) in self._field:
            if not name==None:
                values.append(getattr(self, name))
            else:
                values.append(value)
        return packet.pack(*values)

    def _decode(self, data):
        """Process Packet Data"""
        #print "Packet.decode> ", binascii.b2a_hex(data)
        packet=struct.Struct('!'+string.join(self._format))
        values=packet.unpack_from(data)
        
        ## iterator over both lists simultaneously (python-foo)
        for ((name,expected),value) in map(None,self._field,values):
            if not name==None:
                setattr(self, name, value)
            ## debug
            if(expected!=None and value!=expected):
                print "Packet.decode> %s %02x %02x" %(name, value, expected)
        #if(packet.size != self.length):
        #    print "Packet.decode> length", packet.size, self.length

    ## Context specific units
    
    def _nextTag(self,skip=1):
        tag=self._tag[-1]
        self._tag[-1]+=skip
        return tag

    def _addTag(self,length):
        # tag number | context class | length
        self._add(None,'B',self._nextTag() << 4 | 0x08 | length)  
        #print "Packet._useTag> ", tag
        
    def _openTag(self):
        # tag number | context class | open tag
        tag=self._tag[-1]
        self._tag.insert(0, 0)
        self._add(None,'B', tag << 4 | 0x08 | 0x0e)  

    def _closeTag(self):
        # tag number | context class | close tag
        tag=self._tag[-1]
        self._tag.pop(0)
        self._tag[-1]+=1
        self._add(None,'B', tag << 4 | 0x08 | 0x0f)  

    ## Context Encodings
    
    def _addObjectID(self,type,instance):
        self._addTag(4)
        self._add('object','I',BACnetObjectType[type] << 22 | instance) # object Type
        self.type=type
        self.instance=instance

    def _addPropertyID(self,property):
        self._addTag(1)
        if type(property) is types.StringType:
            property=BACnetPropertyIdentifier[property]
        self._add('property','B',property) # property

    def _addBoolean(self,value,name=None):
        self._addTag(1)
        self._add(name,'B',value)
        
    def _addUnsigned32(self,value,name=None):
        self._addTag(4)
        self._add(name, 'I', value)    

    def _addUnsigned(self,value,name=None):
        self._addTag(2)
        self._add(name, 'H', value)    

    ## Application Primitives
    
    def _Enumerated(self,value,name=None):
        self._add(None,'B',0x91)        # Tag: Enumerated(9) | Application | Length (1)
        self._add(name,'B',value)       # Enumeration (0-255)

        
class RequestPacket(Packet):
    def __init__(self,servicechoice,id=None):
        global LastRequestID
        Packet.__init__(self,0x04,0x00) # Expecting Reply ; Confirmed Request | Unsegmented
        self._add('segment','B',0x04)   # Maximum APDU size 1024
        self._add('id','B',id)          # Request ID
        self._add('servicechoice','B',  # serviceChoice/ACK [no tag]
                  BACnetConfirmedServiceChoice[servicechoice])
        if id==None:
            LastRequestID+=1
            self.id=LastRequestID

class ComplexACK(Packet):
    def __init__(self,servicechoice=None,data=None):
        Packet.__init__(self,0x00,0x30) # Reply ; ComplexACK | Unsegmented
        ## APDU header
        self._add('id','B',None)        # Responding to Request ID
        self._add('servicechoice','B',  # serviceChoice/ACK [no tag]
                  servicechoice and BACnetConfirmedServiceChoice[servicechoice])
        if(data):
            self(data)

class SimpleACK(Packet):
    def __init__(self,request=None,data=None):
        Packet.__init__(self,0x00,0x20)      # Reply Present ; SimpleACK | 0x00
        self._add('id','B',request and request.id)  # original request ID
        self._add('servicechoice','B',request and request.servicechoice)  # serviceChoice/ACK
        if(data):
            self(data)


class ReadPropertyRequest(RequestPacket):
    def __init__(self,type,instance,property='present-value'):
        RequestPacket.__init__(self,'readProperty')
        self._addObjectID(type,instance)    # ObjectIdentifier
        self._addPropertyID(property)       # PropertyIdentifier
        #                                   # PropertyArrayIndex (optional)

class ReadPropertyResponse(ComplexACK):
    def __init__(self,request):
        ComplexACK.__init__(self,'readProperty')
        self._addObjectID(request.type,request.id)  # ObjectIdentifier
        self._addPropertyID(request.property)       # PropertyIdentifier
        self._nextTag()                             # PropertyArrayIndex (Optional)
        ## PropertyValue
        self._openTag()
        self._Enumerated(None,'value')
        self._closeTag()

class SubscribeCOVRequest(RequestPacket):
    def __init__(self,object,lifetime=120):
        RequestPacket.__init__(self,'subscribeCOV')
        self._addUnsigned32(0)      # subscriberProcessIdentifier
        self._addObjectID(*object)  # monitoredObjectIdentifier
        self._addBoolean(False)     # issueConfirmedNotifications
        self._addUnsigned(lifetime) # lifetime


#### Main Class

class BacLog:
    def __init__(self):
        
        ## Configure
        self.config=ConfigParser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        
        ## Load database driver
        self.db=database.Database()
        print "Baclog>", self.config.get('Network','bind'), self.db.database
        
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
        print "Baclog.run>"

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
        
        self.work[request.id]=(request,response,target)
        self.send.append((request,target))
        
        ## subscribe to COV for 2 min.
        subscribe=SubscribeCOVRequest(object)
        self.work[subscribe.id]=(subscribe,SimpleACK(subscribe),target)
        self.send.append((subscribe,target))
        
        self.process()
        print "Baclog.run>", response.value
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
                print "BacLog.process> send:", destination, request.id, request 
                s.sendto(request(),destination)
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
                    r=None ## Thinkgs get hard!
                if r and self.work.has_key(r.id):
                    # remove from work queue and put on done
                    self.work[r.id][1](response)
                    self.done.append(self.work[r.id])
                    del self.work[r.id]
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
