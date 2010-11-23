## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import struct

## PhaseII Data types
class Tagged:
    def __init__(self,data=None,tag=None):
        print "Tagged> %s " % self.__class__
        self._tag=tag     ## Current tag.
        self._value=None  ## Current "Value"
        if data:
            self._decode(data)
            
    def _getTag(self,data=None):
        """Update current tag and return tag value, no data indicates last tag"""
        if data==None:
            return self._tag
        tag=data._get()
        if tag!=None:
            tag,=struct.unpack('!B',tag)
            #print "Tagged.getTag> 0x%02x" % tag, self._decodeTag(tag)
        self._tag=tag
        return tag
        
    def _decodeTag(self,tag=None):
        if tag==None:
            tag=self._tag # Default to current tag
        num=(tag&0xF0)>>4
        cls=(tag&0x08)>>3
        lvt=(tag&0x07)
        return num, cls, lvt
    
    def _openTag(self):
        if self._tag==None:
            return None
        if (self._tag&0x0F)==0x0E:
            return (self._tag&0xF0)>>4
        
    def _closeTag(self,data,tag=None):
        """Returns True if more data until matched tag"""
        if self._getTag(data)==None:
            return None
        if (self._tag&0x0F)!=0x0F:
            return True
        if tag!=None:
            assert (self._tag>>4 == tag)
        return False

## Basic Types        

class Unsigned(Tagged):
    ## decode also used by Bitstring
    def _decode(self, data):
        num,cls,length=self._decodeTag()
        assert length!=3 # unsupported unpack
        self._value,=struct.unpack([None,'!B','!H'][length],data._get(length))
        #print "Unsigned.decode>", self._value

class Unsigned16(Unsigned):
    pass

class Unsigned32(Unsigned):
    pass

class Integer(Tagged):
    pass

class Boolean(Tagged):
    pass

class Enumerated(Unsigned):
    def __str__(self):
        return "%s:%d" % self._display[self._value],self._value
        
class Bitstring(Tagged):
    def _decode(self,data):
        num,cls,length=self._decodeTag()
        assert length!=(3+1) # unsupported unpack
        self._unused,self._value=struct.unpack(['!BB','!BH'][length-2],data._get(length))

class ObjectIdentifier(Tagged):
    def _decode(self,data):
        num,cls,length=self._decodeTag()
        assert length==4
        object,=struct.unpack('!L',data._get(length))
        self.objectType=int((object&0xFFC00000)>>22)
        self.instance=      (object&0x003FFFFF)
        self._value=(self.objectType,self.instance)
        #print "ObjectIdentifier.decode> %08x" % object , self._value

## Composite types

class Application(Tagged):
    _application=[
                  None,         # [A0] NULL
                  None,         # [A1] Boolean
                  Unsigned,     # [A2] Unsigned
                  Integer,      # [A3] Integer
                  None,         # [A4] Float
                  None,         # [A5] Double
                  None,         # [A6] Character
                  None,         # [A7] Unicode
                  Bitstring,    # [A8] Bitstring
                  Enumerated,   # [A9] Enumerated
                  ]
    def _decode(self,data):
        opentag=self._openTag()
        
        tag=self._getTag(data)
        num,cls,lvt=self._decodeTag(tag)
        DataClass = self._application[num]
        element=DataClass(data,tag)
        self._value=element._value
        #print "Application.decode>", element._value

        if opentag!=None:
            self._closeTag(data,opentag)        

class Sequence(Tagged):
    def _decode(self,data):
        opentag=self._openTag()
        print "Sequence.decode> ############", opentag
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag()
            name, DataClass = self._sequence[num]
            element=DataClass(data,self._getTag())
            setattr(self,name,element._value)
            print "Sequence.decode>", name, element._value
        print "Sequence.decode> -----------", opentag
        self._value=self
        
    def _encode(self):
        print "Sequence.encode>"
        return 

class SequenceOf(Tagged):
    def _decode(self,data):
        ## Assume Context Tagging
        opentag=self._openTag() 
        print "SequenceOf.decode> ############", opentag
        ## Only decode sequence of sequence
        assert issubclass(self._sequenceof, Sequence)
        self._value=[self._sequenceof()]
        last=-1
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag()
            if num<=last: ## wrapped [strictly ordered tags]
                self._value.append(self._sequenceof())
            last=num
            name, DataClass = self._sequenceof._sequence[num]
            element=DataClass(data,self._getTag())
            setattr(self._value[-1],name,element._value)
            print "SequenceOf.decode>", len(self._value), name, element._value
        
        print "SequenceOf.decode> ------------", opentag

        ## Magic to make sequenceof to use _sequencekey for attiributes
        if self._sequencekey==None:
            return
        for item in self._value:
            name,cls = self._sequenceof._sequence[self._sequencekey]
            index=getattr(item,name,cls)
            display=cls._display[index]
            assert display not in dir(self) 
            setattr(self,display,item)
        self._value=self
