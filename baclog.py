#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import struct
import string

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
        ## NPDU
        self._add('version','B',0x01)   # ASHRAE 135-1995
        self._add('control','B',0x04)   # Confirmed Request
        ## APDU header
        self._add('pdutype','B',0x00)   # Confirmed Request Unsegmented
        self._add('segment','B',0x04)   # Maximum APDU size 1024
        self._add('id','B',0x00)        # Request ID
        
    def _add(self,name,format,default=None):
        self._field.append((name,default))
        self._format.append(format)
        if name:
            setattr(self, name, default)
        
    def __call__(self):
        packet=struct.Struct('!'+string.join(self._format))
        self.length=packet.size ## self defined
        values=[]
        for (name,default) in self._field:
            if not name==None:
                values.append(getattr(self, name))
            else:
                values.append(default)
        return packet.pack(*values)

    def __str__(self):
        return "%s %d" % (binascii.b2a_hex(self()), self.length)

    
    
    ## Context specific units
    def _addTag(self,length):
        tag=self._tag[-1]
        self._tag[-1]+=1
        self._add(None,'B',tag << 4 | 0x08 | length)  # tag number| context class | length
        #print "Packet._useTag> ", tag
        return tag

    def _addObjectID(self,type,instance):
        self._addTag(4)
        self._add(None,'I',self.BACnetObjectType[type] << 22|instance) # object type

    def _addPropertyID(self,property):
        self._addTag(1)
        self._add(None,'B',self.BACnetPropertyIdentifier[property]) # property
        
    ## Specification Enumerations
    BACnetObjectType = {'binary-input':3,'binary-output':4}
    BACnetPropertyIdentifier = {'present-value':85}


class ReadPropertyRequest(Packet):
    def __init__(self):
        Packet.__init__(self)
        self._add('servicechoice','B',12)       # readProperty(12) [no tag]
        self._addObjectID('binary-output',20)   # ObjectIdentifier
        self._addPropertyID('present-value')    # PropertyIdentifier
                                                # ArrayIndex (optional)

def main():
    print "BacLog.main>"

    ## Invoke 1{8}, Read property, BO instance 20 (0x14), present-value (85).
    message = binascii.unhexlify("810a001101040003010c0c010000141955")
    print binascii.b2a_hex(message)

    ## Generated message
    p=ReadPropertyRequest()
    message=p()
    print p

    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(('192.168.23.53',47808))
    s.setblocking(0)

    send=1
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
            s.sendto(message,('192.168.83.100',47808))
            send-=1
        ## Recv
        if sr and recv:
            (response,source)=s.recvfrom(1500)
            ## Expect 810a0014010030010c0c0100001419553e91003f
            print "BacLog.main> recv:", recv, source, binascii.b2a_hex(response)
            recv-=1
        if se:
            print "BacLog.main> error", se
            
    s.close()

if __name__=='__main__':
    main()

