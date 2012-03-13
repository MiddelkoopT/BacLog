#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser
config=None

import bacnet
import tagged
import scheduler
import message
import service

from objects import Object

import console
import postgres as database

from scheduler import Task
from message import Message

info=True
debug=True
trace=True

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
            if debug: print "GetPresentValue> value:", m.value._value._value
            response=yield database.Log(response.stamp,response.remote[0],response.remote[1],
                                        m.object.type,m.object.instance,m.value._value._value)


class WritePresentValue(Task):
    
    def init(self,target):
        self.target=target
    
    def run(self):
        value=False
        for i in range(0,10):
            value=not value
            wpv=bacnet.WriteProperty()
            wpv._new()
            wpv.object._set('binaryOutput',20)
            wpv.property._set(bacnet.PropertyIdentifier.presentValue)
            wpv.index=None
            wpv.value=bacnet.Property(value,ptype=bacnet.BinaryPV)
            wpv.priority._set(12)
            print "WritePresentValue>",i,wpv
            ack=yield Message(self.target,wpv)
            print ack
            

class SubscribeCOV(Task):
    def run(self):
        while True:
            if debug: print "SubscribeCOV> ** device subscribe:", self.target
            for o in self.target.objects:
                if debug: print "SubscribeCOV>", o, self.target
                subscribe=bacnet.SubscribeCOV()
                subscribe.spid=self.pid
                subscribe.object=o.objectIdentifier
                subscribe.confirmed=False
                subscribe.lifetime=self.lifetime
                for i in range(0,10):
                    ack=yield Message(self.target.address, subscribe)
                    if debug: print "SubscribeCOV> Subscribe ACK", ack
                    if isinstance(ack.message, tagged.Boolean) and ack.message._value==True:
                        break
                    print "SubscribeCOV> Subscribe Error", i, o, ack
                    yield scheduler.Wait(i*6+1)
                    
            yield scheduler.Wait(int(self.lifetime*0.75))


class FindObjects(Task):

    def init(self,devices):
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
            message=bacnet.ReadProperty('objectName',('device',target.device))
            response=yield Message(target.address,message)
            name=response.message.value._value
            response=yield database.Device(target.IP,target.port,target.device,name)
            deviceID,=response.pop()
            
            objects=[]
            index=0
            while True:
                index+=1
                readproperty=bacnet.ReadProperty('objectList',('device',target.device),index)
                request=yield Message(target.address,readproperty)
                if isinstance(request.message, bacnet.Error):
                    break
                
                o=request.message.value[0] ## Object
                if debug: print "FindObjects>", o
                if o.type in ioObjectTypes:
                    objects.append(o)

            if debug: print "FindObjects> ** device objects:",target.device
            for o in objects:
                response=yield Message(target.address,bacnet.ReadProperty('objectName',o))
                name=response.message.value._value
                response=yield Message(target.address,bacnet.ReadProperty('description',o))
                description=response.message.value._value
                if debug: print "FindObjects> name:", name, description
                response=yield database.Object(deviceID,o.type,o.instance,name,description)
                objectID,=response.pop()
                target.objects.append(Object(objectID,o.type,o.instance,name))
                
            if debug: print "FindObjects> ** device end:",target.device

class COVNotification(Task):
    def run(self):
        response=yield None ## bootstrap
        while True:
            if not isinstance(response, Message):
                response=yield None
                continue
            m=response.message
            if debug: print "COVNotification>", m.object, m.values.presentValue._get()
            response=yield database.Log(response.stamp,response.remote[0],response.remote[1],
                                        m.object.type,m.object.instance,m.values.presentValue._get())


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
        name=config.get('Network','name')
        
        ## Object Discovery
        
        bootstrap=config.getboolean('Options','bootstrap')
        if bootstrap==False:
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
                print " ", d.objects

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
        print "BacLog.run> configure"

        table=service.InstanceTable(device,name)
        
        service.register(scheduler,self.mh,service.ReadProperty(device,name,table))
        service.register(scheduler,self.mh,service.ReadPropertyMultiple(device,name,table))
        service.register(scheduler,self.mh,service.WhoIs(device))

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
                
        #for target in devices:
        #    scheduler.add(WritePresentValue(target.address))

        ## Run scheduler.
        print "BacLog.run> run"
        scheduler.run()
        
        ## Terminate
        self.shutdown()

    def shutdown(self):
        self.scheduler.shutdown()

if __name__=='__main__':
    print "BacLog> start"
    main=BacLog()
    main.run()
    print "BacLog> done"
