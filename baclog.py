#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser

## Use which data store.  [Database.driver stores value; not implemented]
#import postgres as database
import console as database

import bacnet
import scheduler
import message

from scheduler import Task
from message import Message

class Test(Task):
    def run(self):
        ## Test packet generation (scheduler conversion)
        request=bacnet.ReadProperty('binary-output',20,'presentValue')
        response=yield Message(('192.168.83.100',47808),request)
        print "Test>", response

class FindObjects(Task):
    def __init__(self,devices):
        Task.__init__(self)
        self.devices=devices
        
    def run(self):
        
        for target,instance in self.devices:
            readproperty=bacnet.ReadProperty('device',instance,'objectList')
            properties=yield Message(target,readproperty)
            print "FindObjects>", properties

        ## subscribe to COV for 2 min.
        subscribe=bacnet.SubscribeCOV()
        subscribe.pid=self.tid
        subscribe.object=bacnet.ObjectIdentifier('binary-output',20)
        subscribe.confirmed=False
        subscribe.lifetime=120
        ack=yield Message(self.devices[0][0], subscribe)
        print "FindObjects>", ack
        
        notification=yield None
        print "FindObjects>", notification


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
        self.scheduler=scheduler.Scheduler()
        self.scheduler.addHandler(message.MessageHandler(bind,port))        
        self.db=database.Database()
        
    def shutdown(self):
        self.scheduler.shutdown()
        exit()

    def run(self):
        ## Read list of devices from database
        devices=self.db.getDevices();
        print "BacLog.run>", devices
        
        scheduler=self.scheduler
        
        #scheduler.add(Test())
        scheduler.add(FindObjects(devices))
        scheduler.run()

        self.shutdown()

if __name__=='__main__':
    main=BacLog()
    main.run()
