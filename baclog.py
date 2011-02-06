#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import binascii
import ConfigParser as configparser

## Use which data store.  [Database.driver stores value; not implemented]
import postgres as database
#import console as database

import bacnet
import scheduler
import message

from scheduler import Task
from message import Message
from binhex import hexbin

debug=True
trace=False


class Test(Task):
    def run(self):
        ## Test packet generation (scheduler conversion)
        request=bacnet.ReadProperty('presentValue','binaryOutput',20,)
        response=yield Message(('192.168.83.100',47808),request)
        print "Test>", response
        
class GetDevices(Task):
    def __init__(self,dbh):
        Task.__init__(self)
        self.dbh=dbh
        self.devices=[]

    def run(self):
        query=self.dbh.query("SELECT IP,port,instance FROM Devices WHERE last IS NULL")
        response=yield query
        self.devices=[]
        for IP,port,instance in response:
            self.devices.append(((IP,port),instance))
        print "GetDevices>", self.devices

class FindObjects(Task):
    def __init__(self,devices):
        Task.__init__(self)
        self.devices=devices
        
    def run(self):
        ## FIXME: Enumerations should be defined this way (convert to undersocre notation).
        ioObjectTypes=[
                       bacnet.ObjectType.binaryOutput, #@UndefinedVariable
                       bacnet.ObjectType.binaryInput,  #@UndefinedVariable
                       ]

        ## Create new notification task.
        pid=Task.scheduler.add(COVNotification())
        
        for target,instance in self.devices:
            readproperty=bacnet.ReadProperty('objectList','device',instance)
            properties=yield Message(target,readproperty)
            for o in properties.message.value:
                if o.objectType not in ioObjectTypes:
                    continue
                if debug: print "FindObjects>", o
                request=bacnet.ReadProperty('presentValue',o)
                response=yield Message(target,request)
                print "FindObjects> value:", response
            
                ## subscribe to COV for 2 min.
                subscribe=bacnet.SubscribeCOV()
                subscribe.pid=pid
                subscribe.object=o
                subscribe.confirmed=False
                subscribe.lifetime=120
                ack=yield Message(target, subscribe)
                print "FindObjects>", ack

class COVNotification(Task):
    def run(self):
        while True:    
            notification=yield None
            print "COVNotification>", notification


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
            whois=yield Message(whois.remote,iam)

class Device:
    _properties=[
                ('protocolServicesSupported',['whoIs','readPropertyMultiple','unconfirmedCOVNotification','readProperty']),
                ('objectName','BL'),
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

#### Main Class

class BacLog:
    def __init__(self):
        ## Configure
        self.config=configparser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        bind=self.config.get('Network','bind')
        port=self.config.getint('Network','port')
        #print "BacLog>"
        
        ## I/O scheduler and drivers
        self.scheduler=scheduler.init()
        self.mh=message.MessageHandler(bind,port)
        self.scheduler.addHandler(self.mh)
        self.dbh=database.DatabaseHandler()
        self.scheduler.addHandler(self.dbh)
        
    def shutdown(self):
        self.scheduler.shutdown()
        exit()

    def run(self):
        ## Runtime information
        scheduler=self.scheduler
        device=self.config.getint('Network','device')

        ## Read list of devices from database
#        db=database.Database()
#        devices=db.getDevices();
#        print "BacLog.run>", devices

        ## Test
        d=Device(device)
        print "###",d.property

        ## Configure using scheduler task GetDevices
        devices=GetDevices(self.dbh)
        scheduler.add(devices)
        scheduler.run()

        ## Add services after information is known
        whois=WhoIs()
        whois.device=device
        scheduler.add(whois)
        self.mh.addService(whois,bacnet.WhoIs)
        
        properties=ReadPropertyMultiple()
        properties.device=device
        properties.name='BacLog'
        scheduler.add(properties)
        self.mh.addService(properties,bacnet.ReadPropertyMultiple)
        
        property=ReadProperty()
        property.device=device
        property.name='BacLog'
        scheduler.add(property)
        self.mh.addService(property, bacnet.ReadProperty)
        
        ## Find objects and register COV
        objects=FindObjects(devices.devices)
        scheduler.add(objects)
        scheduler.run()

        self.shutdown()

if __name__=='__main__':
    main=BacLog()
    main.run()
