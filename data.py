## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

import psycopg2
from stream import Object, Objects

import gzip
import re

from datetime import datetime, timedelta, tzinfo

class TZ(tzinfo):
    def __init__(self,offset):
        self.offset=offset
        self.delta=timedelta(hours=offset)
        self.zero=timedelta(0)
    
    def utcoffset(self, dt):
        return self.delta
    
    def dst(self, dt):
        return self.zero
    
    def tzname(self, dt):
        return "%+02.2d" % self.offset
    
    def __repr__(self):
        return "%+02.2d" % self.offset
    
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

class DataStream:
    def __init__(self,filename,devices,dump=True):
        self.devices=devices
        if not dump:
            self.fh=open(filename,'rb')
            return
        ## Raw dump
        self.fh=gzip.open(filename,'rb')
        for l in self.fh:
            if l[0:8]=='COPY log':
                break
            
    def __iter__(self):
        ## indicators
        start=datetime.now()
        count=0
        maxi=0
        maxd=timedelta(0)

        i=0
        regex=re.compile('^(\d\d\d\d)-([01]\d)-([0-3]\d) ([0-2]\d):([0-6]\d):([0-6]\d)(\.\d+)?([+-]\d\d)$')
        buffer=[]
        for l in self.fh:
            if l=="\\.\n":
                break
            count+=1

            time, ip, port, objectid, type, instance, status, value = l.split("\t")
            ## Data convert (this is why we use databases!)
            port=int(port)
            type=int(type)
            instance=int(instance)
            device=self.devices[(ip,port)]
            value=float(value)
            
            year,month,day,hour,min,sec,micro,tz=regex.match(time).groups()
            ctime=datetime(int(year),int(month),int(day),
                           int(hour),int(min),int(sec),
                           int(float(micro)*1000000) if micro else 0,
                           TZ(int(tz)))
            ## ordered buffer
            event=(ctime,device,type,instance,value)
            for i,e in enumerate(buffer):
                if ctime>=e[0]:
                    break
            buffer.insert(i,event)
            
            ## Monitor
            maxd=max(maxd,buffer[0][0]-buffer[-1][0])
            maxi=max(maxi,i)
            if count%10000==0:
                print count,datetime.now()-start,maxi,maxd
                
            ## fill buffer
            if len(buffer)<100000: ## keep buffer full
                continue
            
            yield buffer.pop() 

        ## drain buffer
        while buffer:
            yield buffer.pop()
        return
