#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser

## Use which data store.  [Database.driver stores value; not implemented]
import postgres as database
#import console as database

import bacnet
import scheduler
import message

from scheduler import Task
from message import Message

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
        for i in range(1,10):    
            notification=yield None
            print "COVNotification>", i, notification


class WhoIs(Task):
    def run(self):
        while True:
            whois=yield None
            print "WhoIs>", whois

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
        ## Read list of devices from database
#        db=database.Database()
#        devices=db.getDevices();
#        print "BacLog.run>", devices
        
        scheduler=self.scheduler
        #scheduler.add(Test())
        
        
        devices=GetDevices(self.dbh)
        scheduler.add(devices)
        scheduler.run()

        ## Services TODO: Add proper conditional so this can be moved to the top
        whois=WhoIs()
        scheduler.add(whois)
        self.mh.addService(whois,bacnet.WhoIs)
        
        objects=FindObjects(devices.devices)
        scheduler.add(objects)
        scheduler.run()

        self.shutdown()

if __name__=='__main__':
    main=BacLog()
    main.run()
