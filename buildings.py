## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Building Customization

import re
import string

tags={'STEAM':'steam', 'STM':'steam', 'CHW':'chw', 'HHW':'hhw', 'APPLICATION':'application'}

class Building:

    def tag(self,instances):
        self._replace(instances) ## string replace
        for o in instances:
            self._tag(o)
        self._fix()
        
    def check(self,instances):
        ## QC check 
        print "untagged", instances.getTagsNot(['room','corridor','closet','mechanical','ahu','pump'])
        print '!descriptor',instances.getTagNot('descriptor')

        print "!building", instances.getTagNot('building')
        print '!vav',instances.getTagsNot(['room','corridor','closet','mechanical']).getTag('vav')
        print '!space',instances.getTagNot('space').getTag('vav')
        print "!unit", instances.getTagNot('unit')
        
        ## Verify VAV box names
        for unit in instances.getValues('unit'):
            r=instances.getTags({'unit':unit,'application':True})
            if len(r)>1:
                print "duplicate unit", r

        for space in instances.getValues('space'):
            r=instances.getTags({'space':space,'application':True})
            if len(r)>1:
                print "duplicate space", r

        for vav in instances.getValues('vav'):
            r=instances.getTags({'vav':vav,'application':True})
            if len(r)>1:
                print "duplicate vav", r
         
    ## Default methods
    replaceUnits=[]
    def _replace(self,instances):
        for s,r in self.replaceUnits:
            for o in instances:
                name=string.replace(o.name,s,r)
                if name!=o.name:
                    o.setTag('fixed',s)
                    o.name=name

    def _fix(self):
        pass

#### Specific Buildings
class Test(Building):
    
    def _tag(self,instance):
        name=instance.name
        print "Test.tag>", name

        for r in re.finditer('^P(\d+)', name):
            instance.setTag('point',int(r.group(1)))
            instance.setTag('unit',name)
            
        if instance.otype==3:
            instance.setTag('input',True)
            instance.setTag('descriptor','input')

        if instance.otype==4:
            instance.setTag('output',True)
            instance.setTag('descriptor','output')


class PughHall(Building):
    ## Rename
    replaceUnits=[
                  ## Series 1
                  ('ROOMTRO1A.VAV127','ROOMTRO2A.VAV124'), # (RV)
                  ('ROOMTRO1A.VAV128','ROOMTRO3A.VAV147'), # (RV)
                  ('ROOM200.VAV127','ROOM250.VAV127'),     # (R)
                  ('PMPMROOM.VAV104','ROOMTRO1A.VAV104'),  # (R)
                  ## Series 2
                  ('RM200.VAV127','RM250.VAV127'),     # 
                  ('PMPROOM.VAV104','RMTRO1A.VAV104'),  #
                   ]         
    
    def _tag(self,instance):
        name=instance.name
        
        ## Building
        for r in re.finditer('^B(\d+)[\._:]', name):
            instance.setTag('building',int(r.group(1)))
            
        ## Derive unit and descriptor/address from name
        for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([:-]([A-Z\d \.-]+))?$', name):
            instance.setTag('unit',r.group(1))
            if r.group(2):
                instance.setTag('descriptor',r.group(3))

        ## Room (rooms can have letters in them!)
        for r in re.finditer('[\._]R(OO)?M(\d+\w*)[\._]', name):
            instance.setTag('room',r.group(2))
            instance.setTag('space',r.group(2))
        
        ## Find Corridor
        for r in re.finditer('[\._](C\d+\w*)[\._]', name):
            instance.setTag('corridor',r.group(1))
            instance.setTag('space',r.group(1))

        ## Find Telcom
        for r in re.finditer('[\._]R(OO)?M(TRO\d+\w*)[\._]', name):
            instance.setTag('closet',r.group(2))
            instance.setTag('space',r.group(2))
            
        ## AHU and other numbered units
        for r in re.finditer('[\._](AHU|VAV|VFD)(\d+)', name):
            tag=string.lower(r.group(1))
            instance.setTag(tag,int(r.group(2)))
            
        ## Find pump VFD's
        for r in re.finditer('[\._]PMP[\._](\d+)[\._]VFD', name):
            instance.setTag('pump',r.group(1))
            instance.setTag('vfd')
            
        ## Find any pump
        for r in re.finditer('[\._](CHW|HHW)?PMP(\d+)[\._:-]', name):
            instance.setTag('pump',int(r.group(2)))
            instance.setTag(string.upper(r.group(1)))
            
        ## Add material tag
        for r in re.finditer("[\._](%s)" % string.join(tags.keys(),'|'), name):
            instance.setTag(tags[r.group(1)])
            
        ## Tag keywords after : or -
        for r in re.finditer('[:-](APPLICATION)$', name):
            if instance.oinstance % 100 == 2:
                instance.setTag(tags[r.group(1)])
                
        ## FLN devices are spaced by 100 >= 10000
        if instance.oinstance >= 10000:
            instance.setTag('module',instance.oinstance/100)
            instance.setTag('address',instance.oinstance%100)
        
        ## MEC I/O < 10000
        if instance.oinstance < 10000:
            for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([\.]([A-Z\d \.-]+))?$', name):
                instance.setTag('unit',r.group(1))
                if r.group(2):
                    instance.setTag('descriptor',r.group(3))
            
        #### Derived information
        
        ## ahu zone
        if instance.hasTag('ahu'):
            instance.setTag('zone',instance.getTag('ahu'))

        ## vav zone Zxx, where z is the zone
        if instance.hasTag('vav'):
            vav=instance.getTag('vav')
            instance.setTag('zone',vav/100)
