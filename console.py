#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Simple console based Database Driver (config comes from baclog.ini

import ConfigParser
import string

class Database:
    def __init__(self,database='Console'):
        self.config=ConfigParser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        self.database=database
        self.port=self.config.getint(database,'port')

    def getDevices(self):
        devices=string.split(self.config.get(self.database,'devices'),',')
        device=0
        database=[]
        for address in devices:
            device+=1
            database.append((device,address,self.port))
        #print "console.Database.getDevices>", database 
        return database
    