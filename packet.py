## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Header packets

import binascii
import struct
import string

class Packet:
    '''Magic Packet Class (somewhat an abstract class).'''

    def __init__(self,control=None,pdu=None,data=None):
        self._field=[]      # (name,value) of variable (None for constant/default)
        self._format=[]     # format of the field
        self._data=None     # unparsed data.
        self._position=0    # beginning of unparsed data.
        self._pdu=None      # payload
        
        ## BVLC
        self._add(None,'B',0x81)            # BACnet/IP
        self._add(None,'B',0x0a)            # UDP
        self._add('_length','H')            # Packet size
        ## NPDU
        self._add('version','B',0x01)       # ASHRAE 135-1995
        self._add('control','B',control)    # NPDU Control; Confirmed Request=0x04
        ## APDU header
        self._add('_pdu','B',pdu)           # (pdutype<<4 | pduflags)
        
        ## Process data and update fields
        data and self._decode(data)
        self._update()

    def _update(self):        
        '''Set computed fields. (pdutype, pduflags)'''
        if(self._pdu!=None):
            self.pdutype=(self._pdu&0xF0) >> 4
            self.pduflags=(self._pdu&0x0F) 

    def _display(self,service):
        return "%s %d" % (binascii.b2a_hex(self._encode(service)), self._length)
        
    def _add(self,name,format,value=None):
        self._field.append((name,value))
        self._format.append(format)
        if name:
            setattr(self, name, value)

    def _encode(self,service):
        '''Generate Packet Data'''
        packet=struct.Struct('!'+string.join(self._format))

        ## Generate payload
        data=service._encode()

        ## Generated fields
        self._length=packet.size+len(data)
        self._pdu=self.pdutype<<4|self.pduflags 

        values=[]
        for (name,value) in self._field:
            #print "Packet.encode>", name, value
            if not name==None:
                value=(getattr(self, name))
            values.append(value)
            assert value!=None ## All fields must have data
        return packet.pack(*values)+data

    def _decode(self, data):
        '''Process Packet Data'''
        #print "Packet.decode> ", binascii.b2a_hex(data)
        packet=struct.Struct('!'+string.join(self._format))
        values=packet.unpack_from(data)
        
        ## iterator over both lists simultaneously (python-foo)
        for ((name,expected),value) in map(None,self._field,values):
            if not name==None:
                setattr(self, name, value)
            ## debug
            if(((not name) or (name and name[0]!='_')) and expected!=None and value!=expected):
                print "Packet.decode> %s %02x %02x" %(name, value, expected)
                assert False ## Should be no unexpected values.

        self._update() ## update computed values

        # Set data protocol
        self._data=data
        self._position=packet.size

    ## Data Protocol
        
    def _get(self,length=1):
        '''Return next slice of data'''
        if self._position+length > len(self._data):
            return None
        self._position+=length
        return self._data[self._position-length:self._position]
    
## Basic PDU types

class ConfirmedRequest(Packet):
    def __init__(self,data=None):
        Packet.__init__(self,0x04,0x00)     # Expecting Reply ; Confirmed Request | Unsegmented
        self._add('_segment','B',0x04)      # Maximum APDU size 1024
        self._add('invoke','B',None)        # Request ID
        self._add('servicechoice','B',None) # serviceChoice/ACK
        if(data):
            self._decode(data)

class UnconfirmedRequest(Packet):
    def __init__(self,data=None):
        Packet.__init__(self,0x00,0x10)     # Not Expecting Reply ; Unconfirmed Request | Unsegmented
        self._add('servicechoice','B',None) # serviceChoice/ACK
        if(data):
            self._decode(data)

class SimpleACK(Packet):
    def __init__(self,data=None):
        Packet.__init__(self,0x00,0x20)     # Reply Present ; SimpleACK | 0x00
        self._add('invoke','B',None)        # original request ID
        self._add('servicechoice','B',None) # serviceChoice/ACK
        if(data):
            self._decode(data)

class ComplexACK(Packet):
    def __init__(self,data=None):
        Packet.__init__(self,0x00,0x30)     # Reply ; ComplexACK | Unsegmented
        self._add('invoke','B',None)        # Responding to Request ID
        self._add('servicechoice','B',None) # serviceChoice/ACK
        if(data):
            self._decode(data)

class Error(Packet):
    def __init__(self,data=None):
        Packet.__init__(self,0x00,0x50)     # Reply ; Error | 0x00
        self._add('invoke','B',None)        # Responding to Request ID
        self._add('servicechoice','B',None) # serviceChoice/Error
        if(data):
            self._decode(data)


## PDU classes indexed by type
PDU=[ConfirmedRequest,UnconfirmedRequest,SimpleACK,ComplexACK,None,Error,None,None]
