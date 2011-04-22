#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser
config=None

import bacnet
import tagged
import scheduler
import message
import service

import object

import console
import postgres as database

from scheduler import Task
from message import Message

info=True
debug=True
trace=False

class Ping(Task):
    def run(self):
        for i in range(1,10):
            ping=yield scheduler.Wait(1)
            print "Ping>",i,ping

class GetPresentValue(Task):
    def run(self):
        if debug: print "GetPresentValue> ** device read values:", self.target
        for o in self.target.objects:
            request=bacnet.ReadProperty('presentValue',o.objectIdentifier)
            response=yield Message(self.target.address,request)
            m=response.message
            if debug: print "GetPresentValue> value:", m.value.value
            response=yield database.Log(response.remote[0],response.remote[1],
                                        m.object.type,m.object.instance,m.value.value)


class SubscribeCOV(Task):
    def run(self):
        while True:
            if debug: print "SubscribeCOV> ** device subscribe:", self.target
            for o in self.target.objects:
                if debug: print "SubscribeCOV>", o, self.target
                subscribe=bacnet.SubscribeCOV()
                subscribe.pid=self.pid
                subscribe.object=o.objectIdentifier
                subscribe.confirmed=False
                subscribe.lifetime=self.lifetime
                for i in range(0,10):
                    ack=yield Message(self.target.address, subscribe)
                    if debug: print "SubscribeCOV> Subscribe ACK", ack
                    if isinstance(ack.message, tagged.Boolean) and ack.message._value==True:
                        break
                    print "SubscribeCOV> Subscribe Error", i, o, ack
                    yield scheduler.Wait(10.0)
                    
            yield scheduler.Wait(int(self.lifetime*0.90))


class FindObjects(Task):
    def __init__(self,devices):
        Task.__init__(self)
        self.devices=devices
        
    def run(self):
        ioObjectTypes=[
                       bacnet.ObjectType.analogInput,  #@UndefinedVariable
                       bacnet.ObjectType.analogOutput, #@UndefinedVariable
                       #bacnet.ObjectType.analogValue,  #@UndefinedVariable
                       bacnet.ObjectType.binaryInput,  #@UndefinedVariable
                       bacnet.ObjectType.binaryOutput, #@UndefinedVariable
                       #bacnet.ObjectType.binaryValue,  #@UndefinedVariable
                       ]

        for target in self.devices:
            if info: print "FindObjects> ** device start:", target
            message=bacnet.ReadProperty('objectName','device',target.device)
            response=yield Message(target.address,message)
            name=response.message.value._value
            response=yield database.Device(target.IP,target.port,target.device,name)
            deviceID,=response.pop()
            
            objects=[]
            index=0
            while True:
                index+=1
                readproperty=bacnet.ReadProperty('objectList','device',target.device,index)
                property=yield Message(target.address,readproperty)
                if isinstance(property.message, bacnet.Error):
                    break
                o=property.message.value[0] ## Object
                if debug: print "FindObjects>", o
                if o.objectType in ioObjectTypes:
                    objects.append(o)

            if debug: print "FindObjects> ** device objects:",target.device
            for o in objects:
                response=yield Message(target.address,bacnet.ReadProperty('objectName',o))
                name=response.message.value._value
                response=yield Message(target.address,bacnet.ReadProperty('description',o))
                description=response.message.value.value
                if debug: print "FindObjects> name:", name, description
                response=yield database.Object(deviceID,o.objectType,o.instance,name,description)
                objectID,=response.pop()
                target.objects.append(object.Object(objectID,o.objectType,o.instance,name))
                
            if debug: print "FindObjects> ** device end:",target.device

class COVNotification(Task):
    def run(self):
        response=yield None ## bootstrap
        while True:
            if not isinstance(response, Message):
                response=yield None
                continue
            m=response.message
            if trace: print "COVNotification>", m.object, m.values.presentValue.value._value.value
            response=yield database.Log(response.remote[0],response.remote[1],m.object.objectType,m.object.instance,m.values.presentValue.value._value.value)


#### Main Class

class BacLog:
    def __init__(self):
        ## Configure
        global config,debug,trace
        config=configparser.ConfigParser()
        config.read(('baclog.ini','local.ini'))
        bind=config.get('Network','bind')
        port=config.getint('Network','port')
        print "BacLog.run> init:", (bind, port)

        if config.getboolean('Options','quiet'):
            debug=False
            trace=False
        
        ## I/O scheduler and drivers
        self.scheduler=scheduler.init()
        self.mh=message.MessageHandler(bind,port)
        self.scheduler.addHandler(self.mh)
        self.dbh=database.DatabaseHandler()
        self.scheduler.addHandler(self.dbh)
        
    def run(self):
        ## Setup scheduler
        scheduler=self.scheduler
        device=config.getint('Network','device')
        
        ## Object Discovery
        
        bootstrap=config.getboolean('Options','bootstrap')
        if not bootstrap:
            ## Configure operation using scheduler task GetDevices
            task=database.GetDevices()
            self.scheduler.add(task)
            self.scheduler.run()
            devices=task.devices
            
        if bootstrap or (not devices):
            ## Use local.ini to get devices.
            db=console.Database()
            devices=db.getDevices();
            objects=FindObjects(devices)
            scheduler.add(objects)
            scheduler.run()

        print "BacLog.run>", devices
        if trace:
            for d in devices:
                print d.objects

        ## Do an initial scan of values and exit
        if config.getboolean('Options','getinitialvalue'):
            for target in devices:
                scan=GetPresentValue()
                scan.target=target
                scheduler.add(scan)
            scheduler.run()
            scheduler.shutdown()
            return

        ## Configure Device

        property=service.ReadProperty()
        property.device=device
        property.name=config.get('Network','name')
        scheduler.add(property)
        self.mh.addService(property, bacnet.ReadProperty)

        properties=service.ReadPropertyMultiple()
        properties.device=device
        properties.name='BacLog'
        scheduler.add(properties)
        self.mh.addService(properties,bacnet.ReadPropertyMultiple)

        whois=service.WhoIs()
        whois.device=device
        scheduler.add(whois)
        self.mh.addService(whois,bacnet.WhoIs)

        cov_pid=scheduler.add(COVNotification())
        
        ## Application
        
        if config.getboolean('Options','subscribeCOV'):
            lifetime=config.getint('Options','lifetime')
            for target in devices:
                cov=SubscribeCOV()
                cov.target=target
                cov.pid=cov_pid
                cov.lifetime=lifetime
                scheduler.add(cov)

        ## Run scheduler.
        scheduler.run()
        
        ## Terminate
        self.shutdown()

    def shutdown(self):
        self.scheduler.shutdown()
        exit()

if __name__=='__main__':
    print "BacLog> start"
    main=BacLog()
    main.run()
    print "BacLog> done"
