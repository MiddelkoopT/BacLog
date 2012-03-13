#!/usr/bin/python
## BacLog Copyright 2012 by Timothy Middelkoop licensed under the Apache License 2.0
## Experiment code.

from time import sleep

from data import Database
import buildings

debug=True
trace=False


class Experiment:

    def run(self):
        print "Experiment.run>"
        
        ## main objects
        db=Database()
        
        ## populate meta information
        objects=db.getObjects()
        #building=buildings.PughHall()
        building=buildings.Test()
        building.tag(objects)
        #building.check(objects)
        
        target=objects.getTag('descriptor','output')
        print target
        
        ## Schedule object.
#        for o in target:
#            db.scheduleObject(o,db.now(-5),10,0)
#            db.scheduleObject(o,db.now(-5),10,1) ## duplicate override

        o=objects.getTag('point',20).single()
        t=db.now()
        db.scheduleObject(o, t+0  , 2.0, 10)
        db.scheduleObject(o, t+2.5, 2.0, 20)
        db.scheduleObject(o, t+1  , 2.5, 30)

        
        ## Retrieve schedule and set control plan.
        for sid,oid,v,active,until in db.getSchedule():
            #print "schedule:", sid,oid,v
            db.setControl(sid,oid,active,until,v)
            
        for c in range(0,60):
            #print "tick %s:" % c
            for sid,oid,v in db.getEnable():
                print "enable %s:" % c, sid,oid
                db.enableInstance(sid)
                db.commandInstance(sid,db.getInstance(oid),v) 

            for sid,oid in db.getDisable():
                print "disable %s:" % c,sid,oid
                db.disableInstance(sid)
                db.commandInstance(sid,db.getInstance(oid),None) 
            sleep(0.1)

        db.close()
        
        ## Monitor section
        
        

## entry point
if __name__=='__main__':
    Experiment().run()
