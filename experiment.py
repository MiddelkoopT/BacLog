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
        o=objects.getTag('point',21).single()
        t=db.now()
        
        db.scheduleObject(o, t+1 , 2, 1)
        db.scheduleObject(o, t+4 , 1, 1)
        db.scheduleObject(o, t+7 , 1, 1)
        db.scheduleObject(o, t+6 , 3, 1)

        db.close()
        
        ## Monitor section
        
        

## entry point
if __name__=='__main__':
    Experiment().run()
