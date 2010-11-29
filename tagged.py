## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import struct
import string
import types
import inspect

import bacnet

## PhaseII Data types
class Tagged:
    _value=None
    def __init__(self,*args,**kwargs):
        '''Init with *args for object creation, **kwargs for decodeing (tag=,data=)'''
        #print "Tagged> %s " % self.__class__, args, kwargs

        ## Little messy but makes objects behave nicely.
        self._tag=kwargs.get('tag',None)     ## Current tag.
        data=kwargs.get('data',None)
        if len(args)>0:
            self._init(*args)
        if data:
            self._decode(data)
            
    def _getTag(self,data=None):
        '''Update current tag and return tag value, no data indicates last tag'''
        if data==None:
            return self._tag
        tag=data._get()
        if tag!=None:
            tag,=struct.unpack('!B',tag)
            #print "Tagged.getTag> 0x%02x" % tag, self._decodeTag(tag)
        self._tag=tag
        return tag
    
    def _setTag(self,num,cls,lvt):
        self._tag=(num << 4) | (cls << 3) | (lvt)
        return self._tag
        
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
        '''Returns True if more data until matched tag'''
        if self._getTag(data)==None:
            return None
        if (self._tag&0x0F)!=0x0F:
            return True
        if tag!=None:
            assert (self._tag>>4 == tag)
        return False

    ## Default methods (should do the right thing)
    
    def _init(self,value):
        '''Default constructor just passes value to self._value'''
        self._value=value

    def _decode(self,data):
        '''Default fixed formatting found in self._format'''
        num,cls,length=self._decodeTag() #@UnusedVariable
        self._value,=struct.unpack(self._format,data._get(length))
        print "Tagged.decode>", self.__class__, self._value

    def _encode(self,tagnum=None):
        '''Default fixed formatting found in self._format'''
        data=struct.Struct('!B'+self._format)
        length=data.size-1
        return data.pack(self._setTag(tagnum,1,length),self._value)


## Basic Types        

class Unsigned(Tagged):
    ## decode also used by Bitstring
    _size=8
    def _decode(self, data):
        '''Variable length decoding of Unsigned'''
        num,cls,length=self._decodeTag() #@UnusedVariable
        assert length<=self._size ## Max sized unsigned
        value=0
        while length:
            byte,=struct.unpack('!B',data._get())
            value=(value<<8)|byte
            length-=1
            #print length,value,byte
        self._value=value         
        #print "Unsigned.decode> %d (%d)" % (self._size, self._value)

    def _encode(self,tagnum):
        '''Variable length encoding of Unsigned'''
        value=self._value
        length=0
        bytes=[]
        while True:
            length+=1
            bytes.insert(0,value & 0xFF)
            value=value>>8
            if value==0:
                break
        #print length, bytes
        assert length<=self._size ## Max sized unsigned
        return struct.pack('!B'+'B'*length,self._setTag(tagnum,1,length),*bytes)

class Unsigned32(Unsigned):
    _size=4

    
class Integer(Tagged):
    pass

class Boolean(Tagged):
    _format='B'

class Enumerated(Unsigned):
    _display=None
    def _init(self,value):
        #print "Enumerated>", self.__class__, value, self._enumeration, self._enumeration[value]
        if type(value) in types.StringTypes:
            value=self._enumeration[value]
        self._value=value

    def __call__(self,key):
        return self._enumerated[key]

    def __str__(self):
        return "%s(%d)" % (self._display[self._value],self._value)

class Bitstring(Tagged):
    def _decode(self,data):
        num,cls,length=self._decodeTag() #@UnusedVariable
        assert length!=(3+1) # unsupported unpack
        self._unused,self._value=struct.unpack(['!BB','!BH'][length-2],data._get(length))

class ObjectIdentifier(Tagged):
    def _decode(self,data):
        num,cls,length=self._decodeTag() #@UnusedVariable
        assert length==4
        object,=struct.unpack('!L',data._get(length))
        self.objectType=int((object&0xFFC00000)>>22)
        self.instance=      (object&0x003FFFFF)
        self._value=(self.objectType,self.instance)
        #print "ObjectIdentifier.decode> %08x" % object , self._value
        
    def _encode(self,tagnum=None):
        '''Encode as application (unsupported) unless tagnum given'''
        return struct.pack('!BI',self._setTag(tagnum,1,4),self.objectType << 22 | self.instance)

    def _init(self,objectType,instance):
        if type(objectType) in types.StringTypes:
            objectType=bacnet.ObjectType._enumeration[objectType]
        self.objectType=objectType
        self.instance=instance
        
    def __repr__(self):
        return "<%s,%d>" % (bacnet.ObjectType._display[self.objectType],self.instance)

class Application(Tagged):
    _application=[
                  None,             # [A0] NULL
                  None,             # [A1] Boolean
                  Unsigned,         # [A2] Unsigned
                  Integer,          # [A3] Integer
                  None,             # [A4] Float
                  None,             # [A5] Double
                  None,             # [A6] Character
                  None,             # [A7] Unicode
                  Bitstring,        # [A8] Bitstring
                  Enumerated,       # [A9] Enumerated
                  None,             # [A10] Date
                  None,             # [A11] Time
                  ObjectIdentifier, # [A12] ObjectIdentifier
                  ]
    
    def _decode(self,data):
        opentag=self._openTag()
        tag=self._getTag(data)
        num,cls,lvt=self._decodeTag(tag) #@UnusedVariable
        DataClass = self._application[num]
        element=DataClass(data=data,tag=tag)
        self.value=element._value
        #print "Application.decode>", element._value

        if opentag!=None:
            self._closeTag(data,opentag)

    def __str__(self):
        return "<%s>" % self.value

## Property's often need context (property,object type) to decde.
class Property(Tagged):
    '''Property -- ugly containment!'''
    _propertymap=None ## delayed initialization
    _type=Application
    def _init(self,object,property):
        print "Property.init>", object, property
        _type=self._propertymap.get(property._value,None) or self._propertymap.get((property,object.objectType),None)
        if _type!=None: ## If none found use default
            self._type=_type
        print "Property.init>", self._type
        
    def _decode(self,data):
        self._value=self._type(data=data,tag=self._tag)

## Composite types

class Sequence(Tagged):
    _sequence=None
    def _decode(self,data):
        opentag=self._openTag()
        #print "Sequence.decode> ############", opentag
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag() #@UnusedVariable
            name, DataClass = self._sequence[num]
            if issubclass(DataClass, Property): ## Hard coded context for Property
                element=Property(self.object,self.property,data=data,tag=self._getTag())._value
            else:
                element=DataClass(data=data,tag=self._getTag())
            setattr(self,name,element)
            #print "Sequence.decode>", name, element
        #print "Sequence.decode> -----------", opentag
        self._value=self
        
    def _encode(self):
        encoded=[]
        for tagnum,(name,cls) in enumerate(self._sequence):
            element=getattr(self,name,None)
            if element==None: continue 
            #print "Sequence.encode>", tagnum, name, cls, element
            if isinstance(element, Tagged):
                encoded.append(element._encode(tagnum))
            else: ## Allow implicet conversion
                encoded.append(cls(element)._encode(tagnum))
        return string.join(encoded,'')
    
    def __str__(self):
        output=["{%s; " % self.__class__]
        for tagnum,(name,cls) in enumerate(self._sequence):
            element=getattr(self,name,None)
            if element==None: continue 
            output.append("%s[%d]:%s, " % (name,tagnum,element))
        output.append("}")
        return string.join(output,'')  

class SequenceOf(Tagged):
    _sequenceof=None
    _sequencekey=None
    def _decode(self,data):
        #print "SequenceOf.decode> ############", opentag
        opentag=self._openTag() 
        assert issubclass(self._sequenceof, Sequence) ## Only decode sequence of sequence
        self._value=[self._sequenceof()]
        last=-1
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag() #@UnusedVariable
            if num<=last: ## wrapped [strictly ordered tags]
                self._value.append(self._sequenceof())
            last=num
            name, DataClass = self._sequenceof._sequence[num]
            element=DataClass(data=data,tag=self._getTag())
            setattr(self._value[-1],name,element)
            #print "SequenceOf.decode>", len(self._value), name, element
        #print "SequenceOf.decode> ------------", opentag

        ## Magic to make sequenceof to use _sequencekey for attiributes
        if self._sequencekey==None:
            return
        for item in self._value:
            name,cls = self._sequenceof._sequence[self._sequencekey]
            index=getattr(item,name,cls)._value
            display=cls._display[index]
            assert display not in dir(self) 
            setattr(self,display,item)
        self._value=self

class Array(Tagged):
    _type=None
    def _decode(self,data):
        opentag=self._openTag()
        #print "Array.decode> ===========", opentag
        self._value=[]
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag() #@UnusedVariable
            item=self._type(data=data,tag=self._getTag())
            self._value.append(item)
            #print "Array.decode>", item
        #print "Array.decode> -----------", opentag

    def __str__(self):
        return str(self._value)

## Helper functions

def buildServiceChoice(base,objects):
    servicechoice={}
    for cls in objects.itervalues():
        if inspect.isclass(cls) and issubclass(cls, base) and hasattr(cls,'_servicechoice'):
            servicechoice[cls._servicechoice]=cls
    return servicechoice

def buildDisplay(objects):
    for cls in objects.itervalues():
        if inspect.isclass(cls) and issubclass(cls, Enumerated) and hasattr(cls, '_enumeration'):
            cls._display=dict((value, key) for key, value in cls._enumeration.iteritems())

def buildProperty(mapping):
    '''Replaces enumerated text values with enumeration values for Property type mapping'''
    _map={}
    for key,value in mapping.items():
        if type(key)!=types.TupleType:
            _map[bacnet.PropertyIdentifier._enumeration[key]]=value
        else:
            _map[(bacnet.PropertyIdentifier._enumeration[key],
                  bacnet.ObjectType._enumeration[key])]=value
    Property._propertymap=_map
