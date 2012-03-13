## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

import time
import psycopg2

from stream import Instance, InstanceList
  
class Database:

    database='baclog'

    def __init__(self):
        self.db=psycopg2.connect(database=self.database)
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
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("""
        SELECT objectid, device,type,instance ,Objects.name,Objects.description
        FROM Objects 
        JOIN Devices USING (deviceID) 
        WHERE Devices.last IS NULL 
        """)
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
    
    def getLastControl(self):
        cur=self.db.cursor()
        cur.execute("SELECT COALESCE(MAX(scheduleID),0) FROM Control")
        return cur.fetchone()

    def getSchedule(self):
        '''Get object that are not yet controlled'''
        cur=self.db.cursor()
        cur.execute("""
        SELECT scheduleID,objectID,value,active,until FROM Schedule
        WHERE scheduleID > %s
        ORDER BY scheduleID
        """, self.getLastControl())
        return cur.fetchall()
    
    def setControl(self,scheduleID,objectID,active,until,value):
        '''Control a point (instance) to value; current schedule'''
        cur=self.db.cursor()
        cur.execute("""
        INSERT INTO Control 
        (scheduleID,objectID,active,until,value,enable,disable) VALUES 
        (%s,%s,%s,%s,%s,FALSE,FALSE)
        """, (scheduleID,objectID,active,until,value))
        
    def getEnable(self,when=None):
        '''Get what should be control at when'''
        if when==None:
            when=psycopg2.TimestampFromTicks(time.time())
        cur=self.db.cursor()
        cur.execute("""
        SELECT scheduleID, objectID, value FROM ( 
          SELECT MAX(scheduleID) AS scheduleID FROM Control
          WHERE %s>active AND %s<until AND enable=FALSE and disable=FALSE
          GROUP BY objectID ) AS selected
        JOIN Control USING (scheduleID)
        """, (when,when))
        return cur.fetchall()
    
    def enableInstance(self,scheduleID):
        '''Turn on enable bit of schedule'''
        cur=self.db.cursor()
        cur.execute("""
        UPDATE Control SET enable=TRUE  WHERE scheduleID=%s;
        UPDATE Control SET disable=TRUE WHERE scheduleID<%s; -- AND enable=TRUE;
        """, (scheduleID,scheduleID))

    def getDisable(self,when=None):
        '''Get active control'''
        if when==None:
            when=psycopg2.TimestampFromTicks(time.time())
        cur=self.db.cursor()
        cur.execute("""
        SELECT scheduleID, objectID FROM Control
        WHERE enable=TRUE AND disable=FALSE AND %s>until
        """, (when,))
        return cur.fetchall()

    def disableInstance(self,scheduleID):
        '''Turn on disable bit of schedule'''
        cur=self.db.cursor()
        cur.execute("""
        UPDATE Control SET disable=TRUE WHERE scheduleID=%s
        """, (scheduleID,))

    def commandInstance(self,scheduleID,instance,value,when=None):
        '''Command object to value'''
        if when==None:
            when=psycopg2.TimestampFromTicks(time.time())
        cur=self.db.cursor()
        cur.execute("""
        INSERT INTO Commands 
        (time,scheduleID,device,type,instance,value,priority) VALUES 
        (%s,%s,%s,%s,%s,%s,12)
        RETURNING commandID
        """, (when,scheduleID,instance.device,instance.otype,instance.oinstance,value))
        commandID=cur.fetchone()[0]
        print "Database.commandObject>", when, scheduleID, instance, value 
        return commandID
        
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
