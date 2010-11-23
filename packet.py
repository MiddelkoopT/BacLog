## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Header packets

import types
import binascii
import struct
import string

import depreciated
from depreciated import *

class RawPacket:
    '''Test packet class (send raw hex encoded packet)'''
    def __init__(self,data=None,pid=None):
        self.data=data
        self.pid=pid
        
    def __call__(self):
        return binascii.unhexlify(self.data)

class Packet:
    '''Magic Packet Class (somewhat an abstract class).'''
    def __init__(self,control=None,pdu=None,data=None):
        self._field=[]      # (name,value) of variable (None for constant/default)
        self._format=[]     # format of the field
        self._tag=[0]       # current context tag
        self._data=None     # unparced data.
        self._position=0    # beginning of unparced data.
        
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
        data and self._decode(data)
        
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
        return "%s %d" % (binascii.b2a_hex(self._encode()), self._length)

    def _encode(self):
        '''Generate Packet Data'''
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
        '''Process Packet Data'''
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

        self._data=data
        self._position=packet.size
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
        self._add('object','I',depreciated.BACnetObjectType[type] << 22 | instance) # object Type
        self.type=type
        self.instance=instance

    def _addPropertyID(self,property):
        self._addTag(1)
        if type(property) is types.StringType:
            property=depreciated.BACnetPropertyIdentifier[property]
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
        
    def _get(self,length=1):
        '''Return next slice of data'''
        if self._position+length >= len(self._data):
            return None
        self._position+=length
        return self._data[self._position-length:self._position]
    
