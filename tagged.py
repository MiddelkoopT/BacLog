## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import struct
import string
import types
import inspect

import bacnet

debug=False
trace=False

## Configuration
SEP="\n"

## Empty Service
class Empty:
    def _encode(self,tagnum=None):
        return ''
    
    def _decode(self,data):
        assert len(data)==0
    
## PhaseII Data types
class Tagged:
    _value=None
    
    def __init__(self,*args,**kwargs):
        '''Init with *args for object creation, **kwargs for decoding (tag=,data=)'''
        #print "Tagged> %s " % self.__class__, args, kwargs


        ## Little messy but makes objects behave nicely.
        self._tag=kwargs.pop('tag',None)     ## Current tag.
        data=kwargs.pop('data',None)
        
        self._init(**kwargs)
        
        if data:
            self._decode(data)
        else:
            self._new()
            if len(args)>0:
                self._set(*args)
            
    def _getTag(self,data=None):
        '''
        Update current tag and return tag value
           None no more data,
           negative lvt indicates open/close tag
        '''
        if data==None:
            return self._tag
        
        ndata=data._get()
        if ndata==None:
            return None
        
        tag,=struct.unpack('!B',ndata)
        num=(tag&0xF0)>>4
        cls=(tag&0x08)>>3
        lvt=(tag&0x07)

        assert num!=0xF   ## unsupported extended tag number
        if lvt<5:
            length=lvt
        elif lvt==5: ## extended length tag
            length,=struct.unpack("!B",data._get())
            assert length!=254 ## unsupported extended lvt
        elif lvt>5:  ## open/close tag
            length=-lvt ## negative indicates open/close       

        self._tag=(num,cls,length)
        #print "Tagged.getTag>", self._tag
        return self._tag
    
    def _setTag(self,num,cls,lvt):
        tag=[]
        fmt='!B'
        ## tag number
        assert num < 0xF  ## tag too large
        ## lvt
        assert lvt < 0xFE ## lvt too large
        if lvt>=0x05: ## Only encodes length
            fmt+='B'
            tag.append(lvt)
            lvt=0x05 ## 8 bit lvt
            
        ## Tag
        tag.insert(0,(num << 4) | (cls << 3) | (lvt))
        return struct.pack(fmt,*tag)
        
    def _openTag(self):
        '''
        Return open tag num if an open tag, otherwise None
        '''
        if self._tag==None:
            return None
        num,cls,lvt=self._tag
        if (cls==1 and lvt==-6): ## application start tag
            return num ## opentag number
        return False ## not an open tag but data.

    def _setOpenTag(self,tagnum=None):
        assert tagnum!=None
        ## do not use setTag, the last arg is length not lvt!
        return struct.pack('!B',(tagnum<<4) | 0x0E)
        
    def _getCloseTag(self,data,opentag):
        '''
        Returns True if more data until matched tag
        '''
        nexttag=self._getTag(data)
        if nexttag==None:
            return None ## no more data
        tag,cls,lvt=nexttag #@UnusedVariable
        if not (cls==1 and lvt==-7): ## not a close tag.
            return True
        assert tag==opentag ## close tag does not have expected tag number
        return False

    def _setCloseTag(self,tagnum):
        assert tagnum!=None
        ## do not use setTag, the last arg is length not lvt!
        return struct.pack('!B',(tagnum<<4) | 0x0F)

    ## Default methods (should do the right thing)
    def _init(self):
        '''
        Setup the object.
        '''
    
    def _new(self):
        '''
        Setup empty object
        '''
    
    def _set(self,value):
        if debug: print "Tagged.set>", self.__class__, value
        self._value=value
        
    def _get(self):
        return self._value

    def _decode(self,data):
        '''Default fixed formatting found in self._format'''
        num,cls,length=self._getTag() #@UnusedVariable
        self._value,=struct.unpack(self._format,data._get(length))
        #print "Tagged.decode>", self.__class__, self._value

    def _encode(self,tagnum=None):
        '''Default fixed formatting found in self._format'''
        data=struct.Struct('!'+self._format)
        length=data.size
        return self._setTag(tagnum,1,length)+data.pack(self._value)

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
        num,cls,length=self._getTag() #@UnusedVariable
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
        data=[]
        while True:
            length+=1
            data.insert(0,value & 0xFF)
            value=value>>8
            if value==0:
                break
        #print length, data
        assert length<=self._size ## Max sized unsigned
        if(tagnum==None):  ## encode as application tag
            tag=self._setTag(self._num,0,length)
        else:
            tag=self._setTag(tagnum,1,length)
        return tag+struct.pack('!'+'B'*length,*data)

class Unsigned32(Unsigned):
    _size=4

class Unsigned16(Unsigned):
    _size=2

class Unsigned8(Unsigned):
    _size=1

class Float(Tagged):
    _format='!f'

class Boolean(Tagged):
    _format='B'
    _num=1 ## Application tag (Boolean encoded as application differently)
    
    def _encode(self,tagnum=None):
        assert self._value is not None ## Boolean value not set
        value=0x01 if self._value else 0x00
        if tagnum==None:
            return self._setTag(0x1,0,value)
        else:
            return self._setTag(tagnum,1,1)+struct.pack('!'+'B',value)

    def _decode(self, data):
        num,cls,lvt=self._getTag() #@UnusedVariable
        if cls==0:
            assert num==1 ## application tag.
            if lvt==0x00:
                self._value=False
            elif lvt==0x01:
                self._value=True
            else:
                assert False ## Invalid Boolean encoding
        else:
            Tagged._decode(self,data)
        #print "Boolean.decode>", self._value

    def __repr__(self):
        if self._value==True or self._value==1:
            return '<True>'
        elif self._value==False or self._value==0:
            return '<False>'
        else:
            return '<None>'

class String(Tagged):
    def _encode(self):
        length=len(self._value)
        data=struct.Struct("!B%ds" % length)
        return self._setTag(0x7,0,length+1)+data.pack(0x00,self._value) ## CharacterString(A7); Encode as UTF-8/ANSI X3.4; string
    
    def _decode(self,data):
        num,cls,length=self._getTag() #@UnusedVariable
        encoding,self._value=struct.unpack("!B%ds" % (length-1),data._get(length))
        assert encoding==0x00
    
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
        #print "Enumerated>", self.__class__, self._value
        return "%s(%d)" % (self._display[self._value],self._value)

class Bitstring(Tagged):
    _field=None
    _size=None
    _display=None
    _num=8 ## application tag number

    def _decode(self,data):
        num,cls,length=self._getTag() #@UnusedVariable
        assert length!=(3+1) # unsupported unpack
        self._unused,self._value=struct.unpack(['!BB','!BH'][length-2],data._get(length))
        
    def _encode(self,tagnum=None):
        assert tagnum==None and self._size==40 ## Only support services supported bitmap (40 bit)
        length=(self._size+7)>>3 ## in bytes.
        data=[0]*length
        for field,value in enumerate(self._value):
            if value:
                data[field>>3] |= 0x80>>(field&0x07) ## set bit.
        return self._setTag(self._num,0,length+1)+struct.pack('!B'+'B'*length,self._size&0x07,*data) ## tag + (unencoded bits, bits)
    
    def _set(self,fields):
        for f in fields:
            self._value[self._field[f]]=1
        
    def _init(self):
        if self._size: ## FIXME: this should be removed, all bit strings should have a defined size
            self._value=[0]*self._size
        
    def __repr__(self):
        output=['<']
        for f,v in enumerate(self._value):
            if v:
                output.append("%s(%d);"% (self._display[f],f))
        output.append('>')
        return string.join(output,'')
        
class ObjectIdentifier(Tagged):
    '''
    ObjectIdentifier(type,instance)
    '''
    _num=12 ## application tag number
    def _decode(self,data):
        num,cls,length=self._getTag() #@UnusedVariable
        assert length==4
        identifier,=struct.unpack('!L',data._get(length))
        self.type=int((identifier&0xFFC00000)>>22)
        self.instance=      (identifier&0x003FFFFF)
        self._value=(self.type,self.instance)
        #print "ObjectIdentifier.decode> %08x" % identifier , self._value
        
    def _encode(self,tagnum=None):
        if tagnum==None:
            tag=self._setTag(self._num,0,4)
        else:
            tag=self._setTag(tagnum,1,4)
        return tag+struct.pack('!I',self.type << 22 | self.instance)

    def _set(self,_type,_instance):
        if type(_type) in types.StringTypes:
            _type=bacnet.ObjectType._enumeration[_type]
        self.type=_type
        self.instance=_instance
        self._value=(self.type,self.instance)
        
    def __hash__(self):
        return hash((self.type,self.instance))
        
    def __repr__(self):
        return "<%s,%d>" % (bacnet.ObjectType._display[self.type],self.instance)


class Property(Tagged):
    '''
    Property -- ugly containment (external context required)!
      properties contain meta-information (property) and a value
    '''
    _identifier=None
    _type=None        ## default type
    _value=None       ## default value

    _propertymap=None ## delayed initialization
    _application=[
                  None,             # [A0] NULL
                  Boolean,          # [A1] Boolean
                  Unsigned,         # [A2] Unsigned
                  None,             # [A3] Integer
                  Float,            # [A4] Float
                  None,             # [A5] Double
                  None,             # [A6] Character
                  String,           # [A7] String
                  Bitstring,        # [A8] Bitstring
                  Enumerated,       # [A9] Enumerated
                  None,             # [A10] Date
                  None,             # [A11] Time
                  ObjectIdentifier, # [A12] ObjectIdentifier
                  ] ## Application map
    
    def _init(self,identifier=None,application=None,ptype=None):
        if identifier:
            self._identifier=identifier
            self._type=self._propertymap.get(identifier._value,None)
        if application:
            assert application in self._application ## unsupported application
            self._type=application
        if ptype:
            self._type=ptype
        
    def _new(self):
        if self._type!=None and issubclass(self._type, (Array,SequenceOf)):
            self._value=self._type()

    def _add(self,*value):
        return self._value._add(*value)

    def _set(self,*value):
        if debug: print "Property.set>", self._identifier, self._type
        if self._type:
            self._value=self._type(*value)
        
                
    def _decode(self,data):
        opentag=self._openTag()
        ## Application
        if self._type==None:
            num,cls,lvt=tag=self._getTag(data) #@UnusedVariable
            self._type=self._application[num]
            if debug: print "Property.decode> Application", num, self._type
            element=self._type(data=data,tag=tag)
            self._value=element
            if debug: print "Property.decode> Application", element._value

        ## Array or SequenceOf (do not read close tag and pass off for further processing)
        elif issubclass(self._type, (Array,SequenceOf)):
            opentag=False
            self._value=self._type(data=data,tag=self._getTag())

        ## Everything else (handle open/close tag here so read tag and process)
        else:
            self._value=self._type(data=data,tag=self._getTag(data))

        if opentag!=False:
            self._getCloseTag(data,opentag)

    def _encode(self,tagnum=None):
        assert tagnum!=None ## Properties use open and close tags.
        if debug: print "Property.encode>", tagnum, self._identifier, self._type
        return self._setOpenTag(tagnum)+self._value._encode()+self._setCloseTag(tagnum)
    
    def _get(self):
        return self._value._get()
    
    def __getitem__(self,index):
        '''
        Get property at index.
        Return a single item as a property (provides context) using the parent property._identifier        
        '''
        assert isinstance(self._value, Array)
        item=Property(identifier=self._identifier)
        item._value=self._value[index]
        return item
        
    def __len__(self):
        assert isinstance(self._value, Array)
        return len(self._value) ## peak into array directly
    
    def __repr__(self):
        if self._identifier==None:
            return repr(self._value)
        return "%s=%s" % (self._identifier, self._value)

## Composite types

class Sequence(Tagged):
    _sequence=None
    _sequencestart=0
    _context=True
    
    def _new(self):
        '''Populate with empty items'''
        for name,DataClass  in self._sequence:
            data=DataClass()
            setattr(self,name,data)
    
    def _decode(self,data):
        opentag=self._openTag()
        start=self._sequencestart
        if debug: print "Sequence.decode> ############", opentag, self.__class__
        tagnum=-1
        while self._getCloseTag(data,opentag):
            num,cls,lvt=self._getTag() #@UnusedVariable
            if not self._context: ## context not encoded
                tagnum+=1
            else:
                tagnum=num+start
            name, DataClass = self._sequence[tagnum]
            if debug: print "Sequence.decode>", name, DataClass
            if issubclass(DataClass, Property): ## Hard coded context for Property
                element=Property(identifier=self.property,data=data,tag=self._getTag())._value
            else:
                element=DataClass(data=data,tag=self._getTag())
            setattr(self,name,element)
            if debug: print "Sequence.decode>", name, DataClass, element
        if debug: print "Sequence.decode> ------------", opentag
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
                if  element._value!=None:
                    encoded.append(element._encode(tagnum))
            else: ## Allow implicit conversion
                encoded.append(cls(element)._encode(tagnum))
        return string.join(encoded,'')
    
    def __repr__(self):
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

    def _add(self):
        new=self._sequenceof()
        new._new()
        self._value.append(new)
        return new

    def _decode(self,data):
        opentag=self._openTag() 
        start=self._sequenceof._sequencestart
        if debug: print "SequenceOf.decode> ############", opentag, self.__class__
        assert issubclass(self._sequenceof, Sequence) ## Only decode sequence of sequence
        self._value.append(self._sequenceof())
        last=-1
        while self._getCloseTag(data,opentag):
            num,cls,lvt=self._getTag() #@UnusedVariable
            if num<=last: ## wrapped [strictly ordered tags]
                self._value.append(self._sequenceof())
            last=num
            name, DataClass = self._sequenceof._sequence[num+start]
            element=DataClass(data=data,tag=self._getTag())
            setattr(self._value[-1],name,element)
            if debug: print "SequenceOf.decode>", len(self._value), name, element
        if debug: print "SequenceOf.decode> ------------", opentag

        ## Magic to make sequenceof to use _sequencekey for attributes
        if self._sequencekey==None:
            return
        #self._index=[]
        for item in self._value:
            name,cls = self._sequenceof._sequence[self._sequencekey+start]
            index=getattr(item,name,cls)._value
            display=cls._display[index]
            assert display not in dir(self) ## detect duplicate index values. 
            setattr(self,display,item)

    def _encode(self,tagnum=None):
        encoded=[]
        for element in self._value:
            encoded.append(element._encode())
        if tagnum:
            encoded.insert(0,self._setOpenTag(tagnum))
            encoded.append(self._setCloseTag(tagnum))
        return string.join(encoded,'')

    def __iter__(self):
        return self._value.__iter__()

    def __repr__(self):
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

    def _init(self):
        #print "Array.init>"
        self._value=[]
        
    def _decode(self,data):
        opentag=self._openTag()
        if trace: print "Array.decode> ===========", opentag
        self._value=[]
        while self._getCloseTag(data,opentag):
            num,cls,lvt=self._getTag() #@UnusedVariable
            item=self._type(data=data,tag=self._getTag())
            self._value.append(item)
            #print "Array.decode>", item
        if trace: print "Array.decode> -----------", opentag
        
    def _encode(self,tagnum=None):
        encoded=[]
        for element in self._value:
            encoded.append(element._encode())
        return string.join(encoded,'')

    def _add(self,*value):
        #print "Array.add>", self.__class__, value
        item=self._type(*value)
        self._value.append(item)
        return item

    def __getitem__(self,index):
        return self._value[index]
    
    def __len__(self):
        return len(self._value)

    def __iter__(self):
        return self._value.__iter__()

    def __repr__(self):
        output=["["]
        for v in self._value:
            output.append(" %s," % v)
        output.append("]")
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
