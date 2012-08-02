## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

import time
import types
import psycopg2

from stream import Instance, InstanceList
  
class Database:

    database='baclog'
    port=5434

    def __init__(self,database=database,port=port):
        self.db=psycopg2.connect(database=database,port=port)
        self.instance={}
        self.objectid={}
        
    def close(self):
        self.db.commit()
        self.db.close()
        
    def getDevices(self):
        devices={}
        cur=self.db.cursor()
        cur.execute("SELECT device,IP,port FROM Devices")
        for device,IP,port in cur:
            devices[(IP,port)]=device
        cur.close()
        return devices
    
    def getObjects(self,where="Devices.last IS NULL"):
        cur=self.db.cursor()
        cur.execute("""
        SELECT objectid, Devices.device,type,instance ,Objects.name,Objects.description
        FROM Objects 
        JOIN Devices USING (deviceID) 
        WHERE %s 
        """% where)
        objects=InstanceList()
        for r in cur:
            objectid,device,otype,oinstance,name,description=r
            o=Instance(device,otype,oinstance)
            o.name=name
            o.id=objectid
            if description != None or description != '':
                o.description=description
            objects.add(o)
            self.instance[(o.device,o.otype,o.oinstance)]=o
            self.objectid[objectid]=o
        cur.close()
        return objects
        
    def getInstance(self,*args):
        ''' Get instance by (device,otype,oinstance)'''
        if len(args)==1:
            return self.objectid[args[0]]
        return self.instance[args]
    
    def getData(self,limit):
        cur=self.db.cursor()
        cur.execute("""
        BEGIN;
        DECLARE cur NO SCROLL CURSOR FOR
            SELECT time,device,type,instance,value FROM Data %s ORDER BY time;
        """ % limit)
        
        return Results(cur);

    def writeTags(self,objects):
        cur=self.db.cursor()
        for o in objects:
            #print "Database.writeTags>", o
            cur.execute("DELETE FROM Tags WHERE objectID=%s", (o.id,))
            for tag,value in o.tags.items():
                #print "#", tag,value
                cur.execute("INSERT INTO Tags (objectID,tag,value) VALUES (%s,%s,%s)", (o.id,tag,value))
        cur.close()

    def writePoints(self,objects):
        cur=self.db.cursor()
        for o in objects:
            #print "Database.writePoints>", o
            cur.execute("DELETE FROM Points WHERE pointID=%s", (o.id,))
            campus=o.getTag('campus')
            building=int(o.getTag('building'))
            for tag,value in o.tags.items():
                #print "#", tag,value
                cur.execute("INSERT INTO Points (pointID,tag,value,active,campus,building) VALUES (%s,%s,%s,%s,%s,%s)",
                            (o.id,tag,value,True,campus,building))
        cur.close()

    def enablePoints(self,objects):
        cur=self.db.cursor()
        for o in objects:
            print "Database.enablePoints>", o
            cur.execute("DELETE FROM Watches WHERE objectID=%s", (o.id,))
            cur.execute("INSERT INTO Watches (objectID,enabled) VALUES (%s,TRUE)", (o.id,))
        cur.close()

    def scheduleObject(self,instance,when,duration,value):
        _when=psycopg2.TimestampFromTicks(when)
        _until=psycopg2.TimestampFromTicks(when+duration)
        cur=self.db.cursor()
        cur.execute("""
        INSERT INTO Schedule 
        (objectID,active,until,value) VALUES
        (%s,%s,%s,%s)
        RETURNING scheduleID; 
        """, (instance.id,_when,_until,value))
        scheduleID=cur.fetchone()[0]
        print "Database.scheduleObject>", scheduleID, instance, value 
        return scheduleID
    
    def execute(self,query):
        cur=self.db.cursor()
        cur.execute(query)
        cur.close()
        
    def now(self,offset=0):
        '''Return current ticks + offset'''
        return time.time()+offset

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
