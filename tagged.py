## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import struct
import string
import types
import inspect

import bacnet

debug=False
trace=False

## Config
SEP="\n"

## PhaseII Data types
class Tagged:
    _value=None
    def __init__(self,*args,**kwargs):
        '''Init with *args for object creation, **kwargs for decodeing (tag=,data=)'''
        #print "Tagged> %s " % self.__class__, args, kwargs

        ## Little messy but makes objects behave nicely.
        self._tag=kwargs.get('tag',None)     ## Current tag.
        data=kwargs.get('data',None)
        
        self._init()
        if len(args)>0:
            self._set(*args)
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
        assert num < 0xF  ## tag too large
        assert lvt < 0x05 ## lvt too large
        self._tag=(num << 4) | (cls << 3) | (lvt)
        return self._tag
        
    def _decodeTag(self,tag=None):
        if tag==None:
            tag=self._tag # Default to current tag
        num=(tag&0xF0)>>4
        cls=(tag&0x08)>>3
        lvt=(tag&0x07)
        assert not (cls==1 and lvt == 0x05) ## length > 4
        assert not (num==0xF)               ## tag > 14
        return num, cls, lvt
    
    def _openTag(self,tagnum=None):
        '''
        if data (no args): returns 
        else: return encoded open tag setting _tag
        '''
        if tagnum!=None:
            assert tagnum < 0xF ## tagnum to large
            self._tag=(tagnum<<4) | 0x0E ## set tag to open tag
            return struct.pack('!B',self._tag)
        if self._tag==None:
            return None
        if (self._tag&0x0F)==0x0E:
            return (self._tag&0xF0)>>4
        
    def _closeTag(self,data=None,tag=None):
        '''
        if data: Returns True if more data until matched tag
        else: returns encoded close tag
        '''
        if data==None:
            assert tag==None ## unsupported nested close tag
            return struct.pack('!B',self._tag | 0x0F)
        if self._getTag(data)==None:
            return None
        if (self._tag&0x0F)!=0x0F:
            return True
        if tag!=None:
            assert (self._tag>>4 == tag)
        return False

    ## Default methods (should do the right thing)
    def _init(self):
        '''Default init does nothing'''
        pass
    
    def _set(self,value):
        '''Default set just passes value to self._value'''
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

    def __repr__(self):
        return "<%s>" % self._value
    
    def __eq__(self,other):
        if isinstance(other, Tagged):
            return self._value==other._value
        return False

    def __ne__(self,other):
        return not self==other
    
    def __hash__(self):
        return self._value.__hash__()

## Basic Types        

class Unsigned(Tagged):
    ## decode also used by Bitstring
    _size=8     # maximum size
    _num=2      # application tag number
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

    def _encode(self,tagnum=None):
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
        if(tagnum==None):  ## encode as application tag
            tag=self._setTag(self._num,0,length)
        else:
            tag=self._setTag(tagnum,1,length)
        return struct.pack('!B'+'B'*length,tag,*bytes)

class Unsigned32(Unsigned):
    _size=4

class Unsigned16(Unsigned):
    _size=2

class Float(Tagged):
    _format='f'

class Boolean(Tagged):
    _format='B'
    def __repr__(self):
        return ['<False>','<True>'][self._value]

class String(Tagged):
    def _encode(self):
        length=len(self._value)
        data=struct.Struct("!BB%ds" % length)
        return data.pack(self._setTag(0x7,0,length+1),0x00,self._value) ## CharacterString(A7); Encode as UTF-8/ANSI X3.4; string

    def __repr__(self):
        return "<'%s'>" % (self._value)
    
class Enumerated(Unsigned):
    _enumeration=None
    _display=None
    _num=9  ## application tag number
    def _set(self,value):
        #print "Enumerated>", self.__class__, value, self._enumeration, self._enumeration[value]
        if type(value) in types.StringTypes:
            value=self._enumeration[value]
        self._value=value

    def __repr__(self):
        return "%s(%d)" % (self._display[self._value],self._value)

class Bitstring(Tagged):
    _field=None
    _size=None
    _display=None
    _num=8 ## application tag number

    def _decode(self,data):
        num,cls,length=self._decodeTag() #@UnusedVariable
        assert length!=(3+1) # unsupported unpack
        self._unused,self._value=struct.unpack(['!BB','!BH'][length-2],data._get(length))
        
    def _encode(self,tagnum=None):
        assert tagnum==None and self._size==40  ## FIXME: Hand packed for size=40 and application
        tag=(self._num<<4) | (0x0 | 0x05) ## Tag 8, application(0), 5=Extended length
        length=(self._size+7)>>3
        bytes=[0]*length
        for field,value in enumerate(self._value):
            if value:
                bytes[field>>3]|= 0x80>>(field&0x07)
        return struct.pack('!BBB'+'B'*length,tag,length+1,self._size&0x07,*bytes) ## tag; extended tag length ; unencoded bits; bits
    
    def _set(self,fields):
        for f in fields:
            self._value[self._field[f]]=1
        
    def _init(self):
        if self._size: ## FIXME: this should be removed, all bit strings should have a defined size
            self._value=[0]*self._size
        
    def __str__(self):
        output=['<<']
        for f,v in enumerate(self._value):
            if v:
                output.append("%s(%d);"% (self._display[f],f))
        output.append('>>')
        return string.join(output,'')
        
class ObjectIdentifier(Tagged):
    _num=12 ## application tag number
    def _decode(self,data):
        num,cls,length=self._decodeTag() #@UnusedVariable
        assert length==4
        object,=struct.unpack('!L',data._get(length))
        self.objectType=int((object&0xFFC00000)>>22)
        self.instance=      (object&0x003FFFFF)
        self._value=(self.objectType,self.instance)
        #print "ObjectIdentifier.decode> %08x" % object , self._value
        
    def _encode(self,tagnum=None):
        if tagnum==None:
            tag=self._setTag(self._num,0,4)
        else:
            tag=self._setTag(tagnum,1,4)
        return struct.pack('!BI',tag,self.objectType << 22 | self.instance)

    def _set(self,objectType,instance):
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
                  None,             # [A3] Integer
                  Float,            # [A4] Float
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
        #print "Application>", num, DataClass
        element=DataClass(data=data,tag=tag)
        self.value=element._value
        #print "Application.decode>", element._value

        if opentag!=None:
            self._closeTag(data,opentag)

    def __str__(self):
        return "<%s>" % self.value

class Property(Tagged):
    '''
    Property -- ugly containment (external context required)!
      properties contain meta-information (property) and a value
    '''
    _property=None
    _propertymap=None ## delayed initialization
    _type=Application ## default type
    def _set(self,property,*value):
        self._property=property
        self._type=self._propertymap.get(property._value,None)  or self._type
        self._value=self._type(*value)
        if debug: print "Property.init>", property, self._type
        
    def _decode(self,data):
        self._value=self._type(data=data,tag=self._tag)
        
    def _encode(self,tagnum=None):
        if debug: print "Property.encode>", tagnum, self._property, self._type
        
        return self._openTag(tagnum)+self._value._encode()+self._closeTag()
                
    def __repr__(self):
        if self._property==None:
            return str(self._value)
        return "%s=%s" % (self._property, self._value)

## Composite types

class Sequence(Tagged):
    _sequence=None
    _sequencestart=0
    _context=True
    
    def New(self):
        '''Populate with empty items'''
        for name,DataClass  in self._sequence:
            data=DataClass()
            if hasattr(data,'New'):
                data.New()
            setattr(self,name,data)
    
    def _decode(self,data):
        opentag=self._openTag()
        start=self._sequencestart
        if debug: print "Sequence.decode> ############", opentag, self.__class__
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag() #@UnusedVariable
            name, DataClass = self._sequence[num+start]
            if issubclass(DataClass, Property): ## Hard coded context for Property
                element=Property(self.property,data=data,tag=self._getTag())._value
            else:
                element=DataClass(data=data,tag=self._getTag())
            setattr(self,name,element)
            if debug: print "Sequence.decode>", name, element
        if debug: print "Sequence.decode> -----------", opentag
        self._value=self
        
    def _encode(self):
        encoded=[]
        for tagnum,(name,cls) in enumerate(self._sequence):
            if not self._context:
                tagnum=None ## application tagging
            else:
                tagnum+=self._sequencestart
            element=getattr(self,name,None)
            if element==None: continue
            if debug: print "Sequence.encode>", tagnum, name, cls, element
            if isinstance(element, Tagged):
                encoded.append(element._encode(tagnum))
            else: ## Allow implicet conversion
                encoded.append(cls(element)._encode(tagnum))
        return string.join(encoded,'')
    
    def __str__(self):
        start=self._sequencestart
        output=["{%s;" % self.__class__]
        for tagnum,(name,cls) in enumerate(self._sequence):
            element=getattr(self,name,None)
            if element==None: continue 
            output.append(" %s[%d]:%s," % (name,tagnum+start,element))
        output.append("}")
        return string.join(output,SEP)  

class SequenceOf(Tagged):
    _sequenceof=None
    _sequencekey=None
    def _init(self):
        self._value=[]

    def Add(self):
        new=self._sequenceof()
        new.New()
        self._value.append(new)
        return new

    def _decode(self,data):
        opentag=self._openTag() 
        start=self._sequenceof._sequencestart
        if debug: print "SequenceOf.decode> ############", opentag, self.__class__
        assert issubclass(self._sequenceof, Sequence) ## Only decode sequence of sequence
        self._value.append(self._sequenceof())
        last=-1
        while self._closeTag(data,opentag):
            num,cls,lvt=self._decodeTag() #@UnusedVariable
            if num<=last: ## wrapped [strictly ordered tags]
                self._value.append(self._sequenceof())
            last=num
            name, DataClass = self._sequenceof._sequence[num+start]
            element=DataClass(data=data,tag=self._getTag())
            setattr(self._value[-1],name,element)
            if debug: print "SequenceOf.decode>", len(self._value), name, element
        if debug: print "SequenceOf.decode> ------------", opentag

        ## Magic to make sequenceof to use _sequencekey for attiributes
        if self._sequencekey==None:
            return
        self._index=[]
        for item in self._value:
            name,cls = self._sequenceof._sequence[self._sequencekey+start]
            index=getattr(item,name,cls)._value
            display=cls._display[index]
            assert display not in dir(self) ## detect duplicate index values. 
            setattr(self,display,item)
        #self._value=self

    def _encode(self,tagnum=None):
        encoded=[]
        for element in self._value:
            encoded.append(element._encode())
        return string.join(encoded,'')

    def __iter__(self):
        return self._value.__iter__()

    def __str__(self):
        start=self._sequenceof._sequencestart
        output=["<<"]
        output.append(SEP)
        for item in self._value:
            for tagnum,(name,cls) in enumerate(self._sequenceof._sequence):
                element=getattr(item,name,None)
                if element==None: continue 
                output.append(" %s[%d]:%s," % (name,tagnum+start,element))
            output.append(SEP)
        output.append(" >>")
        return string.join(output,'')  

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

    def __iter__(self):
        return self._value.__iter__()

    def __str__(self):
        output=["["]
        for v in self._value:
            output.append(" %s," % v)
        output[-1]="]"
        return string.join(output,SEP)

## Helper functions

def buildServiceChoice(base,objects):
    servicechoice={}
    for cls in objects.itervalues():
        if inspect.isclass(cls) and issubclass(cls, base) and hasattr(cls,'_servicechoice'):
            servicechoice[cls._servicechoice]=cls
    return servicechoice

def buildDisplay(objects):
    for cls in objects.itervalues():
        if not inspect.isclass(cls):
            continue
        if issubclass(cls, Enumerated) and cls._enumeration:
            cls._display=dict((value, key) for key, value in cls._enumeration.iteritems())
        if issubclass(cls, Bitstring) and cls._field:
            cls._display=dict((value, key) for key, value in cls._field.iteritems())

def buildEnumeration(objects):
    for cls in objects.itervalues():
        if inspect.isclass(cls) and issubclass(cls, Enumerated) and cls._enumeration:
            for name,value in cls._enumeration.iteritems():
                setattr(cls,name,value)

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
