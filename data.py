## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis Data

import psycopg2
from stream import Object, Objects

import gzip
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
    def __init__(self,filename,devices):
        self.devices=devices
        self.fh=gzip.open(filename,'rb')
        self.last=None
        for l in self.fh:
            if l[0:8]=='COPY log':
                break
        
    def __iter__(self):
        count=0
        skip=0
        start=datetime.now()
        for l in self.fh:
            if l=="\\.\n":
                return
            count+=1
            time, ip, port, objectid, type, instance, status, value = l.split("\t")
            ## Data convert
            port=int(port)
            type=int(type)
            instance=int(instance)
            device=self.devices[(ip,port)]
            value=float(value)
            if len(time[0:-3])==19:
                ctime=datetime.strptime(time[0:-3],'%Y-%m-%d %H:%M:%S')
            else:
                ctime=datetime.strptime(time[0:-3],'%Y-%m-%d %H:%M:%S.%f')
            ctime=ctime.replace(tzinfo=TZ(int(time[-3:])))
            ## drop out of order packets.
            if (self.last is not None) and ctime<self.last:
                #print "DataStream> drop", (ctime,device,type,instance,value)
                skip+=1
                continue
            self.last=ctime
            if count%10000==0:
                print skip, count, 100*skip/count, count*100/42e6,datetime.now()-start
            yield (ctime,device,type,instance,value)
