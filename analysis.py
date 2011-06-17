#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

from stream import Variable, Value, Connection, Stream, Object
from data import Data
import buildings
import graph


class RoomEnthalpy(Stream):
    
    def _init(self,vav):
        self._addIn(vav.getTag('descriptor','AUX TEMP').object(),'sa')
        self._addIn(vav.getTag('descriptor','FLOW').object(),'f')
        self._addIn(vav.getTag('descriptor','CTL FLOW MAX').object(),'mf')
        self._addIn(vav.getTag('descriptor','CTL TEMP').object(),'t')
        
        app=vav.getTag('application').object()
        self._addOut(Variable('hin',app),'hin')
        
        self._addPlot('hin',  (0.121569, 0.313725, 0.552941, 1.0))
        self._addPlot('hout', (1.000000, 0.500000, 0.000000, 1.0))
        self._addPlot('q',    (0.725490, 0.329412, 0.615686, 1.0))
        self._addPlot('hroom',(0.000000, 0.500000, 0.000000, 1.0))
        self._addPlot('error',(1.000000, 0.000000, 0.000000, 1.0))

    def _start(self):
        W=0.008 ## assume humidity ratio of 50% @ 71F
        self.hroom=0.240*self.t+W*(1061+0.444*self.t)
        self.hroom=0 ## FIXME: proper heat loss model needed
        
    def _compute(self,delta):
        #print "RoomEnthalpy.compute>"

        W=0.008 ## assume humidity ratio of 50% @ 71F
        sa,f,mf,t=self._values()[0:4] ## ordered
        
        ## Sensible q estimate 
        cfm=mf*(f/100.0)
        self.q=cfm*1.08*(sa-t)

        ## Mixed air model.  Assume no change in W
        self.hin =0.240*sa+W*(1061+0.444*sa)
        self.hout=0.240*t +W*(1061+0.444*t)
        
        ## mass ratio of exchanged air, use CF/CFM not mass (small temp range)
        mr=(cfm*delta/60.0)/(181*12)  
        self.hroom=mr*(self.hin-self.hout)+(1.0-mr)*self.hroom
        
        self.error=self.hin-self.hout

        
class RoomSum(Stream):

    def _init(self):
        print "RoomSum.init>"
        self._addOut(Variable('hin_sum'),'hin_sum')
        self._addIn(Object(9040,1,12278)) ## FIXME: Hard coded test
        
    def _register(self,var):
        #print "RoomSum.register>", var
        if var in self._input:
            return True
        if var.name=='hin':
            self._addIn(var, 'hin_%d' % var.source.getTag('vav'))
            return True
        return False
        
    def _compute(self,delta):
        #print "RoomSum.compute>",delta,repr(self)
        return True
        
class Source(Stream):
    def _init(self,output):
        for o in output:
            self._addOut(o)
            

class Analysis:

    def run(self):
        print "Analysis.run>"
        data=Data()
        objects=data.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        zone=objects.getTag('zone',1)
        vavs=zone.getValues('vav')
        vavs=[129,130]
        
        ## Build network
        ds=Source('data',zone)
        dc=Connection('data') # data connection
        dc.addIn(ds)
        
        rs=RoomSum('sum')
        rc=Connection('sum') # room connection
        rc.addOut(rs)

        for vav in vavs:
            r=RoomEnthalpy(('VAV%s') % vav,zone.getTag('vav',vav))
            dc.addOut(r)
            rc.addIn(r)
            # connect to sum

        dc.addOut(rs)
                    
        print repr(dc)
        print repr(rc)

        ## Process Data
        for time,device,type,instance,value in data.getData(): ## TODO: Refactor cursor into iter
            v=Value(data.getObject(device,type,instance),value,time,0)
            dc.send(v)
        
        ## Plot
        plot=dc.output[0]
        graph.Graph(plot._plottime,plot._plotdata,plot._plotname).run()


if __name__=='__main__':
    Analysis().run()
    