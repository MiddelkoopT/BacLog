#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import struct
import string
import ConfigParser

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

    def _addPropertyID(self,property):
        self._addTag(1)
        self._add(None,'B',self.BACnetPropertyIdentifier[property]) # property
        
    ## Application Tags
    def _addEnumerated(self,value,name=None):
        self._add(None,'B',0x91)        # Enumerated(9) | Application | Length (1)
        self._add(name,'B',value)       # Enumeration (0-255)
        
    ## Specification Enumerations
    BACnetObjectType = {'binary-input':3,'binary-output':4}
    BACnetPropertyIdentifier = {'present-value':85}

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
    def __init__(self):
        RequestPacket.__init__(self)
        self._add('servicechoice','B',12)       # readProperty(12)/ACK [no tag]
        self._addObjectID('binary-output',20)   # ObjectIdentifier
        self._addPropertyID('present-value')    # PropertyIdentifier
                                                # PropertyArrayIndex (optional)

class ResponsePacket(Packet):
    def __init__(self):
        Packet.__init__(self)
        ## NPDU
        self._add('version','B',0x01)   # ASHRAE 135-1995
        self._add('control','B',0x00)   # Reply
        ## APDU header
        self._add('pdutype','B',0x30)   # ComplexACK Unsegmented
        self._add('id','B',None)        # Responding to Request ID

    def __call__(self, data):
        """Process Packet Data"""
        print "ResponsePacket> ", binascii.b2a_hex(data)
        packet=struct.Struct('!'+string.join(self._format))
        values=packet.unpack_from(data)
        #print self._format
        #print values
        
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
    def __init__(self,data=None):
        ResponsePacket.__init__(self)
        self._add('servicechoice','B',12)       # readProperty() [no tag]
        self._addObjectID('binary-output',20)   # ObjectIdentifier
        self._addPropertyID('present-value')    # PropertyIdentifier
        self._nextTag()                         # PropertyArrayIndex (Optional)
        ## PropertyValue
        self._openTag()
        self._addEnumerated(None,'value')
        self._closeTag()

        if data:
            self(data)
                                                
def main():
    print "BacLog.main>"
    config=ConfigParser.ConfigParser()
    config.read(('baclog.ini','local.ini'))
    PORT=config.getint('Network','port')
    print config.get('Network','bind')

    ## Setup backets
    p=ReadPropertyRequest()
    r=ReadPropertyResponse()

    ## Bind
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind((config.get('Network','bind'),PORT))
    s.setblocking(0)

    ## Loop
    send=2
    recv=send
    
    while(send+recv>0):
        if send:
            (sr,sw,se) = select.select([s],[s],[s])
        else:
            (sr,sw,se) = select.select([s],[],[s])
        print sr,sw,se
        ## Send
        if sw and send:
            print "BacLog.main> send:", send
            p.id=send
            s.sendto(p(),(config.get('Test','target'),PORT))
            send-=1
        ## Recv
        if sr and recv:
            (response,source)=s.recvfrom(1500)
            r(response)
            print "BacLog.main> recv:", recv, r.id, r.value, source, binascii.b2a_hex(response)
            recv-=1
        if se:
            print "BacLog.main> error", se
            
    s.close()

if __name__=='__main__':
    main()
