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
        o=objects.getTag('point',20).single()
        t=db.now()
        db.scheduleObject(o, t+0  , 20, 10)
        db.scheduleObject(o, t+25 , 20, 20)
        db.scheduleObject(o, t+10 , 25, 30)

        db.close()
        
        ## Monitor section
        
        

## entry point
if __name__=='__main__':
    Experiment().run()
