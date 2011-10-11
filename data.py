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
        devices={}
        cur=self.db.cursor()
        cur.execute("SELECT device,name,IP,port FROM Devices")
        for device,name,IP,port in cur:
            devices[(IP,port)]=device
        cur.close()
        return devices
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,type,instance ,Objects.name,Objects.description FROM Devices JOIN Objects USING (deviceID)")
        objects=Objects()
        for r in cur:
            device,otype,oinstance,name,description=r
            o=Object(device,otype,oinstance)
            o.name=name
            if description != None or description != '':
                o.description=description
            objects.add(o)
            self.object[(o.device,o.type,o.instance)]=o
        cur.close()
        return objects
    
    def getObject(self,device,otype,oinstance):
        return self.object[(device,otype,oinstance)]

    def getData(self,query=None):
        ## Feeding data to stream.
        cur=self.db.cursor()
        cur.execute("SELECT time,device,type,instance,value FROM Data %s ORDER BY time " % query)
        print "Data.getData>", cur.rowcount
        return cur

