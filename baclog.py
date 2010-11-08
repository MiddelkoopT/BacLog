#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii
import struct
import string

### Magic Packet Class.
class Packet:
    def __init__(self):
        self._name=[]
        self._format=[]
        
        ## VLC
        self._add('BACnetIP','B',0x81)  # BACnet/IP
        self._add('UDP','B',0x0a)       # UDP
        self._add('length','H')         # Packet size
        ## NPDU
        self._add('version','B',0x01)   # ASHRAE 135-1995
        self._add('control','B',0x04)   # Confirmed Request
        ## APDU header
        self._add('pdu','B',0x00)       # Confirmed Request Unsegmented
        self._add('segment','B',0x04)   # Maximum APDU size 1024
        self._add('id','B',0x00)        # Request ID

        self._packet=struct.Struct('!'+string.join(self._format))
        print self
        
    def _add(self,field,format,default=None):
        self._name.append(field)
        self._format.append(format)
        setattr(self, field, default)
        
    def __call__(self):
        self.length=self._packet.size ## self defined.
        values=[]
        for f in self._name:
            values.append(getattr(self, f))
        return self._packet.pack(*values)

    def __str__(self):
        return "Packet> %s %d" % (binascii.b2a_hex(self()), self.length)


def main():
    print "BacLog.main>"
    p=Packet()
    message=p()

    ## Invoke 1{8}, Read property, BO instance 20 (0x14), present-value (85).
    #message = binascii.unhexlify("810a001101040003010c0c010000141955")
    
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

