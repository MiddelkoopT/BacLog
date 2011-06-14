#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

import psycopg2

from stream import Object, Value, Objects, Connection, RoomEnthalpy
import buildings
import graph
            
            
class Analysis:
    database='mtim'

    def __init__(self):
        print "analysis.py"
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
        return objects

    def run(self):
        print self.getDevices()
        objects=self.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        zone=objects.getTag('zone',1)
        zone=zone.getTag('room','241') ## debug
        vavs=zone.getValues('vav')
        
        ## Build network
        c=Connection()
        for vav in vavs:
            s=RoomEnthalpy(('VAV%s') % vav,zone.getTag('vav',vav))
            c.addOut(s)
            
        c.connect()
        print c

        ## Start feeding data to stream.
        cur=self.db.cursor()
        cur.execute("SELECT time,device,type,instance,value FROM Data ORDER BY Time")
        print cur.rowcount
        for time,device,type,instance,value in cur:
            v=Value(self.object[(device,type,instance)],value,time)
            c.send(v)
        
        graph.Graph(s._plottime,s._plotdata,s._plotname).run()


if __name__=='__main__':
    Analysis().run()
    