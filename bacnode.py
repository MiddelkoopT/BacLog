#!/usr/bin/python
## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0

import ConfigParser as configparser
config=None

import bacnet
import tagged
import scheduler
import message
import service

#### Main Class

class BacNode:
    def __init__(self):
        ## Configure
        global config,debug,trace
        config=configparser.ConfigParser()
        config.read(('baclog.ini','local.ini'))
        bind=config.get('Client','bind')
        port=config.getint('Client','port')
        print "BacLog.run> init:", (bind, port)

        ## I/O scheduler and drivers
        self.scheduler=scheduler.init()
        self.mh=message.MessageHandler(bind,port)
        self.scheduler.addHandler(self.mh)
        
    def run(self):
        ## Setup scheduler
        scheduler=self.scheduler
        device=config.getint('Client','device')
        name=config.get('Client','name')
        
        ## Configure Device
        print "BacLog.run> configure", device
        table=service.InstanceTable(device,name)

        point=service.BinaryOutput(0,'BO_0')
        point.presentValue._value=tagged.Boolean(True)
        table.add(point)

        point=service.BinaryOutput(1,'BO_1')
        point.presentValue._value=tagged.Boolean(True)
        table.add(point)

        readproperty=service.ReadProperty(table)
        scheduler.add(readproperty)
        self.mh.addService(readproperty, bacnet.ReadProperty)

        properties=service.ReadPropertyMultiple(table)
        scheduler.add(properties)
        self.mh.addService(properties,bacnet.ReadPropertyMultiple)

        cov=service.COV(table)
        scheduler.add(cov)
        
        subscribecov=service.SubscribeCOV(table,cov)
        scheduler.add(subscribecov)
        self.mh.addService(subscribecov,bacnet.SubscribeCOV)

        print "BacLog.run> run"
        scheduler.run()
       
        ## Terminate
        self.shutdown()

    def shutdown(self):
        print "BacLog.shutdown>"
        self.scheduler.shutdown()

if __name__=='__main__':
    print "BacNode> start"
    main=BacNode()
    main.run()
    print "BacNode> done"
