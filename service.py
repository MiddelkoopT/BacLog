## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Services

import bacnet
from message import Message
from scheduler import Task

debug=False
trace=False

## Objects

class Device:
    _properties=[
                ('protocolServicesSupported',['whoIs','readPropertyMultiple','unconfirmedCOVNotification','readProperty']),
                ('objectName','BACLOG'),
                ('systemStatus','operational'),
                ('vendorIdentifier',65535),
                ('segmentation','noSegmentation'),
                ('maxAPDU',1024),
                ('maxSegments',1),
                ('APDUSegmentationTimeout',0),
                ('APDURetries',0),
                ('APDUTimeout',0),
                ]
    def __init__(self,device):
        self.property={}
        self._properties.append(('objectIdentifier',('device',device)))
        for property,init in self._properties:
            identifier=bacnet.PropertyIdentifier(property)
            if type(init)==type(tuple()):
                value=bacnet.Property(identifier,*init)
            else:
                value=bacnet.Property(identifier,init)
            self.property[identifier]=value

## Services

class ReadPropertyMultiple(Task):
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
    def run(self):
        request=yield None ## boot
        while True:
            if trace: print "PropertyMultiple>", request
            assert request.message.object.instance==self.device ## support only Device
            device=Device(self.device)
            response=bacnet.ReadPropertyResponse()
            response.object=request.message.object
            response.property=request.message.property
            response.value=device.property[request.message.property]
            response.index=None
            
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

