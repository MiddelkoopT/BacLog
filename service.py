## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Services

import tagged
import bacnet
from message import Message
from scheduler import Task

debug=True
trace=True

## Objects

### TODO: Migrate this to a generic object type and push to bacnet 
### These are not first class objects as there is no ANS.1 Encoding.
### Use a similar object structure and initialization style (ducktype) as bacnet objects.

class Object:
    _otype=None 
    _properties=None
    instance=None
    value=None
    
    def __init__(self,instance,name,*args):
        self.property={}
        self.instance=instance
        self.addProperty('objectIdentifier',(self._otype,instance))
        self.addProperty('objectName',name)

        for name,value in self._properties:
            self.addProperty(name,value)

        self.init(*args)

        
    def addProperty(self,name,value=None):
            pidentifier=bacnet.PropertyIdentifier(name)
            if type(value)==type(tuple()):
                value=bacnet.Property(pidentifier,*value)
            elif value is None:
                value=bacnet.Property(pidentifier) 
            else:
                value=bacnet.Property(pidentifier,value)
            self.property[pidentifier]=value
            assert not hasattr(self,name) ## Duplicate attr
            setattr(self,name,value)
            return value
            
    def init(self):
        '''Custom initialization of Object'''
        pass

class Device(Object):
    instance=None
    _otype='device' ## TODO: change to _type and possibly use "compiled" types 
    _properties=[
                ('protocolServicesSupported',['whoIs','readPropertyMultiple','unconfirmedCOVNotification','readProperty']),
                ('systemStatus','operational'),
                ('vendorIdentifier',65535),
                ('segmentation','noSegmentation'),
                ('maxAPDU',1024),
                ('maxSegments',1),
                ('APDUSegmentationTimeout',0),
                ('APDURetries',0),
                ('APDUTimeout',0),
                ('objectList',None),
                ]
            
class BinaryOutput(Object):
    instance=None
    _otype='binaryOutput'
    _properties=[
                 ('description',''),
                 ]
    
    def init(self):
        self.addProperty('presentValue',tagged.Boolean())
    
## Services

class InstanceTable:
    def __init__(self,device,name):
        self._instance={}
        self._device=Device(device,name)
        self.add(self._device)
        
    def add(self,properties):
        assert properties.instance is not None ## Instance number not set
        identifier=self._device.objectList.Add(properties._otype,properties.instance)
        self._instance[identifier]=properties
        print "InstanceTable.add>", identifier
        
    def __getitem__(self,index):
        return self._instance[index]
        
    def __repr__(self):
        return repr(self._instance)


class ReadPropertyMultiple(Task):

    def init(self,table):
        self.table=table

    def run(self):
        request=yield None ## boot
        while True:
            if trace: print "ReadPropertyMultiple>", request
            response=bacnet.ReadPropertyMultipleResponse()
            for object in request.message:
                assert object.object.instance==self.device ## support only Device
                result=response.Add()
                result.object=object.object
                device=Device(self.device)
                for reference in object.list:
                    value=device.property.get(reference.property,None)
                    if value==None: continue
                    item=result.list.Add()
                    item.property=reference.property
                    item.value=value
                    item.index=None
            
            if trace: print "ReadPropertyMultiple>", request.invoke, response
            request=yield Message(request.remote,response,request.invoke)

class ReadProperty(Task):

    def init(self,table):
        self.table=table
        
    def run(self):
        request=yield None ## boot
        while True:
            if trace: print "ReadProperty>", request
            instance=self.table[request.message.object]
            response=bacnet.ReadPropertyResponse()
            response.object=request.message.object
            response.property=request.message.property
            response.value=instance.property[request.message.property]

            if request.message.index is not None:
                if request.message.index._value > len(response.value): ## 1 based index; bounds error
                    response=bacnet.Error() ## TODO: give proper error value.
                else:
                    response.index=request.message.index._value
                    response.value=response.value[response.index-1] ## 1 based index
                    assert response.index!=0 ## not supported

            if trace: print "ReadProperty>", request.invoke, response
            request=yield Message(request.remote,response,request.invoke)

class WhoIs(Task):

    def run(self):
        whois=yield None ## boot
        while True:
            print "WhoIs>", whois
            iam=bacnet.IAm()
            iam.object=bacnet.ObjectIdentifier('device',self.device)
            iam.maxlength=1024
            iam.segmentation=bacnet.Segmented.noSegmentation #@UndefinedVariable
            iam.vendor=65535
            print "WhoIs>", iam
            whois=yield Message(whois.remote,iam,timeout=None)

