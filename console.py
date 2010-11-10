#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Simple console based Database Driver (config comes from baclog.ini

import ConfigParser
import string

class Database:
    def __init__(self,database='Console'):
        self.config=ConfigParser.ConfigParser()
        self.config.read(('baclog.ini','local.ini'))
        self.database=database # section in option file to store database information
        self.port=self.config.getint(database,'port')

    def getDevices(self):
        devices=string.split(self.config.get(self.database,'devices'),',')
        database=[]
        for address in devices:
            instance=self.config.getint(address,'instance')
            database.append((address,self.port,instance))
        #print "console.Database.getDevices>", database 
        return database
    
    def getObjects(self,address):
        objects=string.split(self.config.get(address,'objects'),',')
        return objects