## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

from datetime import datetime, timedelta, tzinfo

import psycopg2
from stream import Instance, InstanceList
  
class Data:

    database='mtim'

    def __init__(self):
        self.db=psycopg2.connect(database=self.database)
        self.object={}
        
    def getDevices(self):
        devices={}
        cur=self.db.cursor()
        cur.execute("SELECT device,IP,port FROM Devices")
        for device,IP,port in cur:
            devices[(IP,port)]=device
        cur.close()
        return devices
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,type,instance ,Objects.name,Objects.description FROM Devices JOIN Objects USING (deviceID)")
        objects=InstanceList()
        for r in cur:
            device,otype,oinstance,name,description=r
            o=Instance(device,otype,oinstance)
            o.name=name
            if description != None or description != '':
                o.description=description
            objects.add(o)
            self.object[(o.device,o.type,o.instance)]=o
        cur.close()
        return objects
    
    def getObject(self,device,otype,oinstance):
        return self.object[(device,otype,oinstance)]

    def getData(self,limit):
        cur=self.db.cursor()
        cur.execute("""
        BEGIN;
        DECLARE cur NO SCROLL CURSOR FOR
            SELECT time,device,type,instance,value FROM Data %s ORDER BY time;
        """ % limit)
        
        return Results(cur);


class Results:
    def __init__(self,cur):
        self.cur=cur;
        
    def __iter__(self):
        while True:
            self.cur.execute("FETCH FORWARD 1000 FROM cur");
            rows=self.cur.fetchall()
            if rows==[]:
                self.cur.execute("END;")
                return
            for r in rows:
                yield r;
