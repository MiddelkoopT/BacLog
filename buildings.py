## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Building Customization

import re
import string

tags={'STEAM':'steam', 'STM':'steam', 'CHW':'chw', 'HHW':'hhw', 'APPLICATION':'application'}

class Building:

    def tag(self,objects):
        self._replace(objects) ## string replace
        for o in objects:
            self._tag(o)
        self._fix()
        
    def check(self,objects):
        ## QC check 
        print "untagged", objects.getTagsNot(['room','corridor','closet','mechanical','ahu','pump'])
        print '!descriptor',objects.getTagNot('descriptor')

        print "!building", objects.getTagNot('building')
        print '!vav',objects.getTagsNot(['room','corridor','closet','mechanical']).getTag('vav')
        print '!space',objects.getTagNot('space').getTag('vav')
        print "!unit", objects.getTagNot('unit')
        
        ## Verify VAV box names
        for unit in objects.getValues('unit'):
            r=objects.getTags({'unit':unit,'application':True})
            if len(r)>1:
                print "duplicate unit", r

        for space in objects.getValues('space'):
            r=objects.getTags({'space':space,'application':True})
            if len(r)>1:
                print "duplicate space", r

        for vav in objects.getValues('vav'):
            r=objects.getTags({'vav':vav,'application':True})
            if len(r)>1:
                print "duplicate vav", r
         
    ## Default methods
    replaceUnits=[]
    def _replace(self,objects):
        for s,r in self.replaceUnits:
            for o in objects:
                name=string.replace(o.name,s,r)
                if name!=o.name:
                    o.setTag('fixed',s)
                    o.name=name

    def _fix(self):
        pass

#### Specific Buildings

class PughHall(Building):
    ## Rename
    replaceUnits=[
                  ('ROOMTRO1A.VAV127','ROOMTRO2A.VAV124'), # (RV)
                  ('ROOMTRO1A.VAV128','ROOMTRO3A.VAV147'), # (RV)
                  ('ROOM200.VAV127','ROOM250.VAV127'),     # (R)
                  ('PMPMROOM.VAV104','ROOMTRO1A.VAV104'),  # (R)
                   ]         
    
    def _tag(self,object):
        name=object.name
        
        ## Building
        for r in re.finditer('^B(\d+)[\._:]', name):
            object.setTag('building',int(r.group(1)))
            
        ## Derive unit and descriptor/address from name
        for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([:-]([A-Z\d \.-]+))?$', name):
            object.setTag('unit',r.group(1))
            if r.group(2):
                object.setTag('descriptor',r.group(3))

        ## Room (rooms can have letters in them!)
        for r in re.finditer('[\._]ROOM(\d+\w*)[\._]', name):
            object.setTag('room',r.group(1))
            object.setTag('space',r.group(1))
        
        ## Find Corridor
        for r in re.finditer('[\._](C\d+\w*)[\._]', name):
            object.setTag('corridor',r.group(1))
            object.setTag('space',r.group(1))

        ## Find Telcom
        for r in re.finditer('[\._]ROOM(TRO\d+\w*)[\._]', name):
            object.setTag('closet',r.group(1))
            object.setTag('space',r.group(1))
            
        ## AHU and other numbered units
        for r in re.finditer('[\._](AHU|VAV|VFD)(\d+)', name):
            tag=string.lower(r.group(1))
            object.setTag(tag,int(r.group(2)))
            
        ## Find pump VFD's
        for r in re.finditer('[\._]PMP[\._](\d+)[\._]VFD', name):
            object.setTag('pump',r.group(1))
            object.setTag('vfd')
            
        ## Find any pump
        for r in re.finditer('[\._](CHW|HHW)?PMP(\d+)[\._:-]', name):
            object.setTag('pump',int(r.group(2)))
            object.setTag(string.upper(r.group(1)))
            
        ## Add material tag
        for r in re.finditer("[\._](%s)" % string.join(tags.keys(),'|'), name):
            object.setTag(tags[r.group(1)])
            
        ## Tag keywords after : or -
        for r in re.finditer('[:-](APPLICATION)$', name):
            if object.instance % 100 == 2:
                object.setTag(tags[r.group(1)])
                
        ## FLN devices are spaced by 100 > 10000
        if object.instance >= 10000:
            object.setTag('module',object.instance/100)
            object.setTag('address',object.instance%100)
            
        #### Derived information
        
        ## ahu zone
        if object.hasTag('ahu'):
            object.setTag('zone',object.getTag('ahu'))

        ## vav zone Zxx, where z is the zone
        if object.hasTag('vav'):
            vav=object.getTag('vav')
            object.setTag('zone',vav/100)
