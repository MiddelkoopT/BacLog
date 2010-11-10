#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import struct
import string
import ConfigParser

# Use which data store.  [Database.driver stores value; not implemented so pydev will follow]
#import postgres as database
import console as database

### Magic Packet Class (somewhat an abstract class).
class Packet:
    def __init__(self):
        self._field=[]      # (name,value) of variable (None for constant/default)
        self._format=[]     # format of the field
        self._tag=[0]       # current context tag
        
        ## VLC
        self._add('BACnetIP','B',0x81)  # BACnet/IP
        self._add('UDP','B',0x0a)       # UDP
        self._add('length','H')         # Packet size
        
    def _add(self,name,format,value=None):
        self._field.append((name,value))
        self._format.append(format)
        if name:
            setattr(self, name, value)
        
    def __str__(self):
        return "%s %d" % (binascii.b2a_hex(self()), self.length)

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

    def _addObjectID(self,type,instance):
        self._addTag(4)
        self._add(None,'I',self.BACnetObjectType[type] << 22|instance) # object type
        self.type=type
        self.instance=instance

    def _addPropertyID(self,property):
        self._addTag(1)
        self._add(None,'B',self.BACnetPropertyIdentifier[property]) # property
        self.property=property
        
    ## Application Tags
    def _addEnumerated(self,value,name=None):
        self._add(None,'B',0x91)        # Enumerated(9) | Application | Length (1)
        self._add(name,'B',value)       # Enumeration (0-255)
        
    ## Specification Enumerations
    BACnetObjectType = {'binary-input':3,'binary-output':4, 'device':8}
    BACnetPropertyIdentifier = {'present-value':85, 'object-list':76}

class RequestPacket(Packet):
    def __init__(self):
        Packet.__init__(self)
        ## NPDU
        self._add('version','B',0x01)   # ASHRAE 135-1995
        self._add('control','B',0x04)   # Confirmed Request
        ## APDU header
        self._add('pdutype','B',0x00)   # Confirmed Request Unsegmented
        self._add('segment','B',0x04)   # Maximum APDU size 1024
        self._add('id','B',0x01)        # Request ID

    def __call__(self):
        """Generate Packet Data"""
        packet=struct.Struct('!'+string.join(self._format))
        self.length=packet.size ## self defined

        values=[]
        for (name,value) in self._field:
            if not name==None:
                values.append(getattr(self, name))
            else:
                values.append(value)
        return packet.pack(*values)

class ReadPropertyRequest(RequestPacket):
    def __init__(self,type,instance,property='present-value'):
        RequestPacket.__init__(self)
        self._add('servicechoice','B',12)       # readProperty(12)/ACK [no tag]
        self._addObjectID(type,instance)   # ObjectIdentifier
        self._addPropertyID(property)    # PropertyIdentifier
        #                                       # PropertyArrayIndex (optional)

class ResponsePacket(Packet):
    def __init__(self,data=None):
        Packet.__init__(self)
        ## NPDU
        self._add('version','B',0x01)   # ASHRAE 135-1995
        self._add('control','B',0x00)   # Reply
        ## APDU header
        self._add('pdutype','B',0x30)   # ComplexACK Unsegmented
        self._add('id','B',None)        # Responding to Request ID
        if(data):
            self(data)

    def __call__(self, data):
        """Process Packet Data"""
        #print "ResponsePacket> ", binascii.b2a_hex(data)
        packet=struct.Struct('!'+string.join(self._format))
        values=packet.unpack_from(data)
        
        ## iterator over both lists simultaneously (python-foo)
        for ((name,expected),value) in map(None,self._field,values):
            if not name==None:
                setattr(self, name, value)
            ## debug
            #print "ResponsePacket> %s %02x" %(name, value),
            #if expected!=None:
            #    print " %02x" % expected,
            #print
        #print "ResponsePacket> length", packet.size, self.length

class ReadPropertyResponse(ResponsePacket):
    def __init__(self,request):
        ResponsePacket.__init__(self)
        self._add('servicechoice','B',12)           # readProperty() [no tag]
        self._addObjectID(request.type,request.id)  # ObjectIdentifier
        self._addPropertyID(request.property)       # PropertyIdentifier
        self._nextTag()                             # PropertyArrayIndex (Optional)
        ## PropertyValue
        self._openTag()
        self._addEnumerated(None,'value')
        self._closeTag()

                                                
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
        self.recv=[] # response queue
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
        target=(devices[0][0],devices[0][1]) ## ugh!
        objects=self.db.getObjects(target[0])
        print "BacLog.run>", target, objects

        ## Setup test packets
        request=ReadPropertyRequest('binary-output',20)
        response=ReadPropertyResponse(request)

        ## insert some work on queue (test to target)
        self.work[request.id]=(request,response,target)
        self.send.append((request,target))
        self.recv.append(response)
        
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
                print "BacLog.process> send:", destination, request 
                s.sendto(request(),destination)
            ## Recv
            if sr:
                (response,source)=s.recvfrom(1500)
                r=ResponsePacket(response)
                print "BacLog.process> recv:", source, r.id, binascii.b2a_hex(response)
                if self.work.has_key(r.id):
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
