#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

from stream import Variable, Value, Connection, Stream, InstanceList
from data import Data
import buildings
import graph

import hvac

class Zone(Stream):
    _monitor=[
              ('AUX TEMP','sa'),
              ('FLOW','pf'), # percent flow
              ('CTL FLOW MAX','mf'),
              ('CTL TEMP','t')
              ]

    def _init(self,vav,rh,sat):

        ## AHU values to monitor
        self._addIn(rh,'rh')
        self._addIn(sat,'sat')
        
        ## Monitor the following VAV values
        for descriptor,name in self._monitor:
            var=vav.getTag('descriptor',descriptor).single()
            var.name=name
            self._addIn(var,name)

        ## derived variables for output
        app=vav.getTag('application').single()
        self._addOut(Variable('f',app),'f')
        self._addOut(Variable('q',app),'q')
        
        ## cache vav.
        self.vav=app.getTag('vav')


    def _compute(self,value,delta):
        '''
        Compute Q
        
        Assumptions: 
         * rh of room is return rh for ahu
         * no losses in ducts.
        '''
        #print "Zone.compute>"
        self.f=self.pf*self.mf
        self.q=self.f*4.5*( hvac.h(self.sa,self.rh) - hvac.h(self.sat,self.rh) )
        
        ## DEBUG
        debug=[129,114]
        if self.vav in debug:
            print "Zone.compute>", self.vav, self.sat, self.sa, self.f, self.rh, self.q
    
class Total(Stream):
    
    def _init(self,vavs):
        print "Total.init>", vavs
        self.vavs=vavs
        self.f={}
        self.q={}
    
    def _register(self,var):
        #print "Total.register>", var
        assert var not in self._input ## duplicate register
        self._addIn(var)
        return True
    
    def _start(self):
        ## Populate t, sa, f by vodo
        for var,value in self._value.items():
            if var.name in ['f','q']:
                getattr(self,var.name)[var.getTag('vav')]=value.value
    
    def _compute(self,value,delta):
        #print "Total.compute>", self._name,
        vav=value.var.getTag('vav')
        if value.var.name in ['f','q']:
            getattr(self,value.var.name)[vav]=value.value
        
        ## could be more intelligent about this.... incremental update.
        qsum=0.0
        for q in self.q.itervalues():
            qsum+=q
            
        #print q, self.q
        

class Source(Stream):

    def _init(self):
        pass
            
    def addOut(self,output):
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
        
        ## Compute streams
        data=Source('data')
        total={}

        ## Connections 
        source=Connection('source') # data connection
        source.addIn(data)
        dest={}

        ## Build network
        ahus=[1,3]
        for ahu in ahus:
            zone=objects.getTag('zone',ahu)
            data.addOut(zone)

            vavs=zone.getValues('vav')
            total[ahu]=Total("total%d" % ahu,vavs)

            dest[ahu]=Connection("dest%d" % ahu)     # total connection
            dest[ahu].addOut(total[ahu]) ## zone totalizer

            ## locally of interest variables
            rh=objects.getTags({'ahu':ahu,'descriptor':'RAIR-H'}).single()
            sat=objects.getTags({'ahu':ahu,'descriptor':'SAIR-TE'}).single()

            for vav in vavs:
                z=Zone(('zone-VAV%s') % vav,zone.getTag('vav',vav), rh,sat) ## Zone stream
                source.addOut(z)
                dest[ahu].addIn(z)
            
        print "Analysis.run>", repr(source)
        print "Analysis.run>", repr(dest)

        ## Process DataStream
        limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-27 22:00'"
        #limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-28 07:00'"
        #limit=None

        
        monitor=InstanceList()
        monitor.add(objects.getTags({'descriptor':'SAIR-TE'}))
        monitor.add(objects.getTags({'descriptor':'RAIR-H'}))
        monitor=monitor.getTag('ahu',1)
        monitor.add(objects.getTags({'vav':129,'descriptor':'CTL TEMP'}))

        i=0;
        for time,device,otype,oinstance,value in db.getData(limit):
            v=Value(db.getObject(device,otype,oinstance),value,time,0)
            source.send(v) ## input data
            
            ## Debug
            if v.var in monitor:
                print "DATA:", v
            
            ## Tick
            if i%1000==0:
                print "TICK:", i,time
            i+=1
             
             
## Main entry point
if __name__=='__main__':
    profile=False
    if not profile:
        Analysis().run()
    else:
        import cProfile
        import pstats
        cProfile.run('Analysis().run()', 'analysis.prof')
        p = pstats.Stats('analysis.prof')
        p.sort_stats('cumulative').print_stats(20)
