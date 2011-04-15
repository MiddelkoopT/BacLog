#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser

import console
import postgres as database
## Site configuration database. [Database.driver stores value; not implemented]
#import postgres as config
#import console as config

import bacnet
import scheduler
import message
import service

from scheduler import Task
from message import Message

debug=True
trace=False

## Hard coded config (bad!)
LIFETIME=3600
LOCALCONFIG=True
SUBSCRIBECOV=False
GETPRESENTVALUE=False

class Ping(Task):
    def run(self):
        for i in range(1,10):
            ping=yield scheduler.Wait(1)
            print "Ping>",i,ping

class FindObjects(Task):
    def __init__(self,devices):
        Task.__init__(self)
        self.devices=devices
        
    def run(self):
        ioObjectTypes=[
                       bacnet.ObjectType.analogInput,  #@UndefinedVariable
                       bacnet.ObjectType.analogOutput, #@UndefinedVariable
                       bacnet.ObjectType.binaryOutput, #@UndefinedVariable
                       bacnet.ObjectType.binaryInput,  #@UndefinedVariable
                       ]

        ## Create new notification task.
        pid=Task.scheduler.add(COVNotification())
        while True:
            for target,instance in self.devices:
                if debug: print "FindObjects> ** device start:",instance
                response=yield Message(target,bacnet.ReadProperty('objectName','device',instance))
                name=response.message.value._value
                response=yield database.Device(target[0],target[1],instance,name)
                
                objects=[]
                index=0
                while True:
                    index+=1
                    readproperty=bacnet.ReadProperty('objectList','device',instance,index)
                    property=yield Message(target,readproperty)
                    if isinstance(property.message, bacnet.Error):
                        break
                    o=property.message.value[0] ## Object
                    if debug: print "FindObjects>", o
                    if o.objectType in ioObjectTypes:
                        objects.append(o)

                if debug: print "FindObjects> ** device objects:",instance
                for o in objects:
                    response=yield Message(target,bacnet.ReadProperty('objectName',o))
                    name=response.message.value._value
                    response=yield Message(target,bacnet.ReadProperty('description',o))
                    description=response.message.value.value
                    if debug: print "FindObjects> name:", name, description
                    response=yield database.Object(instance,None,o.instance,o.objectType,name,description)
                    
                if GETPRESENTVALUE:
                    if debug: print "FindObjects> ** device read values:",instance
                    for o in objects:
                        request=bacnet.ReadProperty('presentValue',o)
                        response=yield Message(target,request)
                        m=response.message
                        if debug: print "FindObjects> value:", m.value.value
                        response=yield database.Log(response.remote[0],response.remote[1],m.object.instance,m.value.value)

                    
                if SUBSCRIBECOV:
                    if debug: print "FindObjects> ** device subscribe:",instance
                    for o in objects:
                        subscribe=bacnet.SubscribeCOV()
                        subscribe.pid=pid
                        subscribe.object=o
                        subscribe.confirmed=False
                        subscribe.lifetime=LIFETIME
                        ack=yield Message(target, subscribe)
                        if trace: print "FindObjects> Subscribe ACK", ack
                    yield scheduler.Wait(LIFETIME-300)

                if debug: print "FindObjects> ** device end:",instance

class COVNotification(Task):
    def run(self):
        response=yield None ## bootstrap
        while True:
            if not isinstance(response, Message):
                response=yield None
                continue
            m=response.message
            if debug: print "COVNotification>", m.object, m.values.presentValue.value._value.value
            response=yield database.Log(response.remote[0],response.remote[1],m.object.instance,m.values.presentValue.value._value.value)


#### Main Class

class BacLog:
    def __init__(self):
        ## Configure
        self.config=configparser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        bind=self.config.get('Network','bind')
        port=self.config.getint('Network','port')
        print "BacLog.run> init:", (bind, port)
        
        ## I/O scheduler and drivers
        self.scheduler=scheduler.init()
        self.mh=message.MessageHandler(bind,port)
        self.scheduler.addHandler(self.mh)
        self.dbh=database.DatabaseHandler()
        self.scheduler.addHandler(self.dbh)
        
    def run(self):
        ## Configure Device
        device=self.config.getint('Network','device')
        if(LOCALCONFIG):
            ## Use local.ini to get devices.
            db=console.Database()
            devices=db.getDevices();
        else:
            ## Configure operation using scheduler task GetDevices
            task=database.GetDevices()
            self.scheduler.add(task)
            self.scheduler.run()
            devices=task.devices

        print "BacLog.run>", devices

        ## Setup scheduler
        scheduler=self.scheduler
        
        ## Add services after information is known
        whois=service.WhoIs()
        whois.device=device
        scheduler.add(whois)
        self.mh.addService(whois,bacnet.WhoIs)
        
        properties=service.ReadPropertyMultiple()
        properties.device=device
        properties.name='BacLog'
        scheduler.add(properties)
        self.mh.addService(properties,bacnet.ReadPropertyMultiple)
        
        property=service.ReadProperty()
        property.device=device
        property.name='BacLog'
        scheduler.add(property)
        self.mh.addService(property, bacnet.ReadProperty)
        
        ## Find objects and register COV
        objects=FindObjects(devices)
        scheduler.add(objects)
        scheduler.run()

        ## Terminate
        self.shutdown()

    def shutdown(self):
        self.scheduler.shutdown()
        exit()

if __name__=='__main__':
    main=BacLog()
    main.run()
