## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

import psycopg2
from stream import Object, Objects

class Data:

    database='mtim'

    def __init__(self):
        self.db=psycopg2.connect(database=self.database)
        self.object={}
        
    def getDevices(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,name FROM Devices")
        devices=cur.fetchall()
        cur.close()
        return devices
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,type,instance ,Objects.name,Objects.description FROM Devices JOIN Objects USING (deviceID)")
        objects=Objects()
        for r in cur:
            device,type,instance,name,description=r
            o=Object(device,type,instance)
            o.name=name
            if description != None or description != '':
                o.description=description
            objects.add(o)
            self.object[(o.device,o.type,o.instance)]=o
        cur.close()
        return objects
    
    def getObject(self,device,type,instance):
        return self.object[(device,type,instance)]

    def getData(self):
        
        ## Feeding data to stream.
        cur=self.db.cursor()
        cur.execute("SELECT time,device,type,instance,value FROM Data ORDER BY Time")
        print "Data.getData>", cur.rowcount
        return cur
