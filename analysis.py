#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

import psycopg2
import re
import string

class Object:
    def __init__(self,_device,_type,_instance):
        self.device=_device
        self.type=_type
        self.instance=_instance
        self.tags={}
        ## Backnet information
        self.name=None
        self.description=None

    def __repr__(self):
        output=["<%s,%s,%s>[%s" % (self.device,self.type,self.instance,self.name)]
        if self.description:
            output.append(';'+self.description)
        output.append(']{')
        tags=[]
        for t,v in self.tags.items():
            if v is True:
                tags.append(t)
            else:
                tags.append('%s:%s' % (t,v))
        output.append(string.join(tags,', '))
        output.append('}')
        return string.join(output,'')
        
    
    def addTag(self,name,value=True):
        self.tags[name]=value
        
    def hasTag(self,tag):
        return self.tags.has_key(tag)
    
    def getTags(self):
        return self.tags.keys()
    
    def tag(self):
        ## auto tagging heuristics
        
        ## Building
        for r in re.finditer('^B(\d+)[\._:]', self.name):
            self.addTag('building',int(r.group(1)))

        ## Room/AHU and other numbered units
        for r in re.finditer('[\._](ROOM|AHU|VAV|VFD)(\d+)', self.name):
            tag=string.lower(r.group(1))
            self.addTag(tag,int(r.group(2)))
        
        ## Find closets
        for r in re.finditer('[\._](C\d+[A-Z])[\._]', self.name):
            self.addTag('closet',r.group(1))

        ## Find Telcom
        for r in re.finditer('[\._]ROOM(TR[A-Z\d]+)[\._]', self.name):
            self.addTag('closet',r.group(1))
            self.addTag('telcon')
            
        ## Find Other
        for r in re.finditer('[\._](PMPM)ROOM[\._]', self.name):
            self.addTag('closet',string.upper(r.group(1)))
            
        ## Find pump VFD's
        for r in re.finditer('[\._]PMP[\._](\d+)[\._]VFD', self.name):
            self.addTag('pump',r.group(1))
            self.addTag('vfd')
            
        ## Find any pump
        for r in re.finditer('[\._](CHW|HHW)?PMP(\d+)[\._:-]', self.name):
            self.addTag('pump',int(r.group(2)))
            self.addTag(string.upper(r.group(1)))
            
        ## Add material tag
        map={'STEAM':'steam', 'STM':'steam', 'CHW':'chw', 'HHW':'hhw'}
        for r in re.finditer("[\._](%s)" % string.join(map.keys(),'|'), self.name):
            self.addTag(map[r.group(1)])
            
        ## derive unit and descriptor/address from name
        for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([:-]([A-Z\d \.-]+))?$', self.name):
            self.addTag('unit',r.group(1))
            if r.group(2):
                self.addTag('descriptor',r.group(3))
            
        ## Tag keywords after : or -
        map={'APPLICATION':'application'}
        for r in re.finditer('[:-](APPLICATION)$', self.name):
            if self.instance % 100 == 2:
                self.addTag(map[r.group(1)])
                
        ## FLN devices are spaced by 100 > 10000
        if self.instance >= 10000:
            self.addTag('module',self.instance/100)
            self.addTag('address',self.instance%100)
            
            
class Objects:
    def __init__(self,objects):
        self.objects=objects    
            
    def __iter__(self):
        return self.objects.__iter__()

    def __repr__(self):
        if not self.objects:
            return '[]'
        output=['[']
        for o in self.objects:
            output.append(str(o))
        output.append(']')
        return string.join(output,"\n  ")

    def tag(self):
        for o in self.objects:
            o.tag()
        ## System wide
        #self.tagUnits()
    
    def getTag(self,tag,value=None):
        result=[]
        for o in self.objects:
            if o.hasTag(tag):
                result.append(o)
        return Objects(result)

    def getTagNot(self,tag):
        result=[]
        for o in self.objects:
            if not o.hasTag(tag):
                result.append(o)
        return Objects(result)

    def getTagsNot(self,tags):
        result=[]
        for o in self.objects:
            found=False
            for t in tags:
                if t in o.getTags():
                    found=True
            if not found:
                result.append(o)
        return Objects(result)
    
class Analysis:
    database='mtim'

    def __init__(self):
        print "analysis.py"
        self.db=psycopg2.connect(database=self.database)
        
    def getDevices(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,name FROM Devices")
        devices=cur.fetchall()
        cur.close()
        return devices
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,type,instance ,Objects.name,Objects.description FROM Devices JOIN Objects USING (deviceID)")
        objects=[]
        for r in cur:
            device,type,instance,name,description=r
            o=Object(device,type,instance)
            o.name=name
            if description != None or description != '':
                o.description=description
            objects.append(o)
        return Objects(objects)

    def run(self):
        print self.getDevices()
        objects=self.getObjects()
        objects.tag()
        
        ## QC check               
        print "!building", objects.getTagNot('building')
        print '!room vav',objects.getTagsNot(['room','closet']).getTag('vav')
        print "!unit", objects.getTagNot('unit')
        
        print "untaged", objects.getTagsNot(['room','closet','ahu','pump'])
        print '!descriptor',objects.getTagNot('descriptor')

        #print objects
        


if __name__=='__main__':
    Analysis().run()
    