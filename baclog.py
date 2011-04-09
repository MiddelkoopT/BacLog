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

debug=False
trace=False

## Hard coded config (bad boy)
LIFETIME=300
LOCALCONFIG=True
SUBSCRIBECOV=True

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
                       bacnet.ObjectType.binaryOutput, #@UndefinedVariable
                       bacnet.ObjectType.binaryInput,  #@UndefinedVariable
                       ]

        ## Create new notification task.
        pid=Task.scheduler.add(COVNotification())
        while True:
            for target,instance in self.devices:
                readproperty=bacnet.ReadProperty('objectList','device',instance)
                properties=yield Message(target,readproperty)
                for o in properties.message.value:
                    if o.objectType not in ioObjectTypes:
                        continue
                    if debug: print "FindObjects>", o
                    request=bacnet.ReadProperty('presentValue',o)
                    response=yield Message(target,request)
                    if trace: print "FindObjects> value:", response

                    ## TEST
                    
                    ## Log value
                    m=response.message
                    response=yield database.Log(response.remote[0],response.remote[1],m.object.instance,m.value.value)
                    yield scheduler.Wait(.1) ## DELAY
                    
                    ## Name
                    request=bacnet.ReadProperty('description',o)
                    response=yield Message(target,request)
                    if debug: print "FindObjects> value:", response
                    
                    ## /TEST
                    if not SUBSCRIBECOV: continue
                    
                    ## SubscribeCOV
                    subscribe=bacnet.SubscribeCOV()
                    subscribe.pid=pid
                    subscribe.object=o
                    subscribe.confirmed=False
                    subscribe.lifetime=LIFETIME
                    ack=yield Message(target, subscribe)
                    if debug: print "FindObjects> Subscribe ACK", ack
            yield scheduler.Wait(1)
            #yield scheduler.Wait(LIFETIME-90)

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
