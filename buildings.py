## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Building Customization

import re
import string

tags={'STEAM':'steam', 'STM':'steam', 'CHW':'chw', 'HHW':'hhw', 'EFAN':'efan', 'OA':'oa', 'APPLICATION':'app'}

class Building:

    def tag(self,instances):
        self._translate(instances) ## character replacement
        self._replace(instances) ## string replace
        for o in instances:
            self._tag(o)
        self._fix(instances)
        
    def check(self,instances):
        ## QC check 
        for n in ['campus','building','unit','num','attr','index']:        
            print "!%s" % n
            for i in instances.getTagNot(n):
                print i,i.name

        print "untagged", instances.getTagsNot(['room','corridor','closet','mechanical','ahu','pump'])

        print '!vav',instances.getTagsNot(['room','corridor','closet','mechanical']).getTag('vav')

        print '!space'
        for o in instances.getTagNot('space').getTag('vav'):
            print o,o.name,o.tags
        
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

    def _translate(self,instances):
        for o in instances:
            o.name=string.replace(o.name,' ','_')

    def _fix(self,instances):
        pass

#### Specific Buildings
class Test(Building):
    
    def _tag(self,instance):
        name=instance.name
        print "Test.tag>", name

        for r in re.finditer('^P(\d+)', name):
            p=int(r.group(1))
            instance.setTag('point',p)

            instance.setTag('campus','uf')
            instance.setTag('building',24)
            instance.setTag('unit','pxc')
            instance.setTag('num','379')
            instance.setTag('attr','point')
            instance.setTag('index',str(p))

            instance.setTag('nn',"uf.24.pxc.379.point.%d" % p)

        if instance.otype==1:
            instance.setTag('output',True)
            instance.setTag('attr','LAO')
            instance.setTag('nn',"uf.24.pxc.379.LAO.%d" % p)
            
        if instance.otype==3:
            instance.setTag('input',True)
            instance.setTag('attr','input')
            instance.setTag('nn',"uf.24.pxc.379.LDI.%d" % p)

        if instance.otype==4:
            instance.setTag('output',True)
            instance.setTag('attr','LDO')
            instance.setTag('nn',"uf.24.pxc.379.LDO.%d" % p)



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
                  ('CHW.KILOTONS','CHW00-KILOTONS')
                   ]         
    
    def _tag(self,instance):
        name=instance.name
        
        ## Campus and Building
        for r in re.finditer('^B(\d+)[\._:]', name):
            instance.setTag('campus','UF')
            instance.setTag('building',int(r.group(1)))
            
        ## Derive unit and attr/address from name
        for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([:-]([A-Z\d \._-]+))?$', name):
            if r.group(2):
                attr=string.lower(string.replace(r.group(3),'.','_'))
                instance.setTag('attr',attr)
                instance.setTag('property',r.group(3))

        ## Room (rooms can have letters in them!)
        for r in re.finditer('[\._]R(OO)?M(\d+\w*)[\._]', name):
            instance.setTag('space',r.group(2))
            instance.setTag('room',r.group(2))
        
        ## Find Corridor
        for r in re.finditer('[\._](C\d+\w*)[\._]', name):
            instance.setTag('space',r.group(1))
            instance.setTag('corridor',r.group(1))

        ## Find Telcom
        for r in re.finditer('[\._]R(OO)?M(TRO\d+\w*)[\._]', name):
            instance.setTag('closet',r.group(2))
            instance.setTag('space',r.group(2))

        ## Add material tag
        for r in re.finditer("[\._](%s)" % string.join(tags.keys(),'|'), name):
            instance.setTag('unit',tags[r.group(1)])
            instance.setTag('num',1)
            
        ## AHU and other numbered units
        for r in re.finditer('[\._](AHU|VAV|VFD)(\d+)', name):
            unit=r.group(1)
            num=int(r.group(2))
            instance.setTag('unit',string.upper(unit))
            instance.setTag('num',num)
            instance.setTag(string.lower(unit),num)
            
        ## Find pump VFD's
        for r in re.finditer('[\._]PMP[\._](\d+)[\._]VFD', name):
            vfd=int(r.group(1))
            instance.setTag('unit','VFD')
            instance.setTag('num',r.group(1))

            instance.setTag('pump',vfd)
            instance.setTag('vfd')
            
        ## Find any pump
        for r in re.finditer('[\._](CHW|HHW)?PMP(\d+)[\._:-]', name):
            instance.setTag('pump',int(r.group(2)))
            instance.setTag(string.upper(r.group(1)))
            
        ## Tag keywords after : or -
        for r in re.finditer('[:-](APPLICATION)$', name):
            if instance.oinstance % 100 == 2:
                instance.setTag(tags[r.group(1)])
                
        ## FLN devices are spaced by 100 >= 10000
        if instance.oinstance >= 10000:
            instance.setTag('module',instance.oinstance/100)
            instance.setTag('address',instance.oinstance%100)

        #### Device
        instance.setTag('device',instance.device)

        #### Derived information
        
        ## ahu zone
        if instance.hasTag('ahu'):
            instance.setTag('zone',instance.getTag('ahu'))

        ## vav zone Zxx, where z is the zone
        if instance.hasTag('vav'):
            vav=instance.getTag('vav')
            instance.setTag('zone',vav/100)
            
        ## indexes (none for now)
        instance.setTag('index',1)
            
        ## Normalized Name
        nn=string.join((instance.getTag('campus'),str(instance.getTag('building')),
                        instance.getTag('unit'),str(instance.getTag('num')),
                        instance.getTag('attr'),str(instance.getTag('index'))),'.')
        instance.setTag('nn',nn)
