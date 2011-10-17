#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

from stream import Variable, Value, Connection, Stream, Instance
from data import Data
import buildings
import graph


class Zone(Stream):
    _monitor=[
              ('AUX TEMP','sa'),
              ('FLOW','pf'), # percent flow
              ('CTL FLOW MAX','mf'),
              ('CTL TEMP','t')
              ]

    def _init(self,vav):
        ## register descriptor/name and add as output
        for descriptor,name in self._monitor:
            var=vav.getTag('descriptor',descriptor).single()
            var.name=name
            self._addIn(var,name)
            if name in ['sa','t']:
                self._addOut(var,name)
            
        ## derived variable
        app=vav.getTag('application').single()
        self._addOut(Variable('f',app),'f')
                    
    def _compute(self,delta):
        #print "Zone.compute>"
        #print self._name,self.sa,self.t,self.f
        self.f=self.pf*self.mf
    
class Total(Stream):
    
    def _init(self):
        #print "Total.init>"
        pass

    def _register(self,var):
        #print "Total.register>", var
        assert var not in self._input ## duplicate register
        self._addIn(var)
        return True
        
    def _compute(self,delta):
        pass
#        for value in self._value.values():
#            print value.var.name,value.value,
#        print

class Source(Stream):

    def _init(self,output):
        for o in output:
            self._addOut(o)

    def send(self,value):
        for c in self._connections:
            c.send(value)
            

class Analysis:

    def run(self):
        print "Analysis.run>"
        
        db=Data()
        #devices=data.getDevices()
        objects=db.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        zone=objects.getTag('zone',1)
        vavs=zone.getValues('vav')
        
        ## Compute streams
        data=Source('data',zone)
        total=Total('total')

        source=Connection('source') # data connection
        source.addIn(data)
        dest=Connection('dest')     # total connection
        dest.addOut(total)
        
        for vav in vavs:
            z=Zone(('zone-VAV%s') % vav,zone.getTag('vav',vav)) ## Zone stream
            source.addOut(z)
            dest.addIn(z)
            
        print "Analysis.run>", repr(source)
        print "Analysis.run>", repr(dest)

        ## Process DataStream
        #limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-27 22:00'"
        limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-28 07:00'"
        #limit=None

        i=0;
        for time,device,itype,instance,value in db.getData(limit):
            v=Value(db.getObject(device,itype,instance),value,time,0)
            source.send(v) ## input data
            if i%100000==0:
                print i,time
            i+=1
             
if __name__=='__main__':
    profile=True
    if not profile:
        Analysis().run()
    else:
        import cProfile
        import pstats
        cProfile.run('Analysis().run()', 'analysis.prof')
        p = pstats.Stats('analysis.prof')
        p.sort_stats('cumulative').print_stats(20)

