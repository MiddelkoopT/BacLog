#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

from stream import Variable, Value, Connection, Stream, Object
from data import Data
import buildings
import graph


class Zone(Stream):
    
    def _init(self,vav):
        self._addIn(vav.getTag('descriptor','AUX TEMP').object(),'sa')
        self._addIn(vav.getTag('descriptor','FLOW').object(),'f')
        self._addIn(vav.getTag('descriptor','CTL FLOW MAX').object(),'mf')
        self._addIn(vav.getTag('descriptor','CTL TEMP').object(),'t')
        
        app=vav.getTag('application').object()
        self._addOut(Variable('hin',app),'hin')
        
        self._addPlot('sa',  (0.121569, 0.313725, 0.552941, 1.0))
        self._addPlot('t',    (1.000000, 0.500000, 0.000000, 1.0))
        self._addPlot('f',    (0.725490, 0.329412, 0.615686, 1.0))

    def _start(self):
        pass
        
    def _compute(self,delta):
        #print "RoomEnthalpy.compute>"
        #print self._name,self.sa,self.t,self.f
        return True
    
class Total(Stream):
    
    def _init(self):
        print "Total.init>"
        
    def _register(self,var):
        print "Total.register>", var
        if var in self._input:
            return True
        return True
        
    def _compute(self,delta):
        repr(self)
        return True

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
        data=Data()
        #devices=data.getDevices()
        objects=data.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        zone=objects.getTag('zone',1)
        #vavs=zone.getValues('vav')
        vavs=[125, 128]
        
        ## Build network
        source=Source('source',zone)
        connection=Connection('connection') # data connection
        connection.addIn(source)
        
        #total=Total('total')
        
        for vav in vavs:
            r=Zone(('zone-VAV%s') % vav,zone.getTag('vav',vav))
            connection.addOut(r)

        #connection.addOut(total)
        print repr(connection)

        ## Process DataStream
        for time,device,itype,instance,value in data.getData("WHERE time >= '2011-09-27 20:00' AND time <= '2011-09-28 07:00'"):
            v=Value(data.getObject(device,itype,instance),value,time,0)
            source.send(v)
        
        ## Plot
        plot=graph.Graph()
        plot.add(connection.output[0],'solid')
        plot.add(connection.output[1],'dash')
        plot.run()

if __name__=='__main__':
    #import cProfile
    #cProfile.run('Analysis().run()', 'analysis.prof')
    Analysis().run()
