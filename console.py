## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Simple console based Database Driver (config comes from baclog.ini)

import ConfigParser
import string
import object

class Database:
    def __init__(self,database='Console'):
        self.config=ConfigParser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        self.database=database # section in option file to store database information
        self.port=self.config.getint(database,'port')

    def getDevices(self):
        devices=string.split(self.config.get(self.database,'devices'),',')
        database=[]
        for d in devices:
            address,instance=d.split('!')
            device=object.Device(address,self.port,int(instance))
            database.append(device)
        #print "console.Database.getDevices>", database 
        return database
    
    def getObjects(self,address):
        objects=[]
        for o in string.split(self.config.get(address[0],'objects'),','):
            t,i=o.split(':')
            objects.append((t,int(i)))
        return objects
