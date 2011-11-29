#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

from stream import Variable, Value, Connection, Stream, InstanceList
from data import Database
import buildings
from graph import Graph, Series

import hvac

debug=True
trace=False

class AHU(Stream):
    _monitor=[
              ('SAIR-TE','sat'),
              ('RAIR-H','rh'),
              ]

    def _init(self,ahu,ahuvars):

        ## Monitor the following values
        for descriptor,name in self._monitor:
            var=ahuvars.getTag('descriptor',descriptor).single()
            var.name=name
            self._addIn(var,name)
            self._addOut(var,name) ## pass through
            assert var.getTag('ahu')==ahu # more than one ahu supplied 
        self.ahu=ahu
        
    def _compute(self,value,delta):
        pass


class Zone(Stream):
    _monitor=[
              # VAV
              ('AUX TEMP','sa'),
              ('FLOW','pf'), # percent flow
              ('CTL FLOW MAX','mf'),
              ('CTL TEMP','t'),
              ]

    def _init(self,vav,ahu):

        ## Monitor the following VAV values
        for descriptor,name in self._monitor:
            var=vav.getTag('descriptor',descriptor).single()
            var.name=name
            self._addIn(var,name)

        ## AHU input
        self._addIn(ahu.getTag('descriptor','RAIR-H').single(),'rh')
        self._addIn(ahu.getTag('descriptor','SAIR-TE').single(),'sat')

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
        #print "Plot.compute>", self.vav, self.sat, self.sa, self.f, self.rh, self.q


class Total(Stream):
    
    def _init(self,vavs):
        #print "Total.init>", self._name, vavs
        self.vavs=vavs
        self.f={}
        self.q={}
        self._addOut(Variable("%s-qsum" % self._name),'qsum')
    
    def _register(self,var):
        #print "Total.register>", self._name, var
        assert var not in self._input ## duplicate register
        self._addIn(var)
        return True
    
    def _start(self):
        ## Populate t, sa, f by voodoo
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
        
        self.qsum=qsum
        

class Data(Stream):

    def _init(self):
        pass
            
    def addOut(self,output):
        for o in output:
            self._addOut(o)

    def send(self,value):
        for c in self._connections:
            c.send(value)

class Plot(Stream):
    
    def _init(self):
        
        self._plot=Series(self._name)

    def _register(self,var):
        print "Plot.register>", var
        assert var not in self._input ## duplicate register
        self._addIn(var)
        self._plot.addLine("%s" % (var.name))
        return True
        
    def _compute(self,value,delta):
        name="%s" % (value.var.name)
        self._plot.add(name,value)
        #print "Plot.compute>", name, value

######
## Main class

class Analysis:

    def run(self):
        print "Analysis.run>"
        
        ## main objects
        db=Database()
        graph=Graph()
        
        ## populate meta information
        #devices=data.getDevices()
        objects=db.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        ## Compute streams
        data=Data('data')
        total={}
        plot=Plot("plot")
        
        ## Connections 
        source=Connection('source') # data connection
        dest={} ## Zone connections
        output=Connection("output")
        
        ## Connect
        source.addIn(data)

        ## Build network
        ahus=[1,3]
        for ahu in ahus:
            zone=objects.getTag('zone',ahu) ## All zone objects (VAV and AHU)
            data.addOut(zone)
            
            vavs=zone.getValues('vav')
            total[ahu]=Total("total%d" % ahu,vavs)
            dest[ahu]=Connection("dest%d" % ahu)
            dest[ahu].addOut(total[ahu]) ## zone totalizer

            a=AHU("ahu%d" % ahu, ahu,objects.getTag('ahu',ahu))
            source.addOut(a)

            for v in vavs:
                z=Zone(('zone%d-VAV%s') % (ahu,v),zone.getTag('vav',v), objects.getTag('ahu',ahu)) ## Zone stream
                source.addOut(z)
                dest[ahu].addIn(z)

            ## Per ahu plots
            output.addIn(total[ahu])

        ## connect plot (last)
        output.addOut(plot)

        if trace:
            print "Analysis.run>", repr(source)
            print "Analysis.run>", repr(dest)
            print "Analysis.run>", repr(total)
            print "Analysis.run>", repr(plot)

        ## Process DataStream
        limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-27 23:00'"
        #limit="WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-28 07:00'"
        #limit=None
        
        ## Debug
        monitor=InstanceList()
        
        #monitor.add(objects.getTags({'descriptor':'SAIR-TE'}))
        #monitor.add(objects.getTags({'descriptor':'RAIR-H'}))
        #monitor=monitor.getTag('ahu',1)

        #monitor.add(objects.getTags({'vav':114,'descriptor':'CTL TEMP'}))
        #monitor.add(objects.getTags({'vav':114,'descriptor':'FLOW'}))
        #monitor.add(objects.getTags({'vav':114,'descriptor':'HTG LOOPOUT'}))
        #monitor.add(objects.getTags({'vav':114}))

        #monitor=InstanceList() ## Disable monitoring
        
        ## Stream compute
        i=0;
        for time,device,otype,oinstance,value in db.getData(limit):
            v=Value(db.getObject(device,otype,oinstance),value,time,0) ## Build value
            data.send(v) ## input data
            
            ## Debug
            if v.var in monitor:
                if v.value!=0:
                    print "DATA:", time, v
            
            ## Tick
            if i%100000==0:
                print "TICK:", i,time
            i+=1
        
        ## Plot
        graph.add(plot)
        graph.run()


## entry point
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
