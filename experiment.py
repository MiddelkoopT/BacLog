#!/usr/bin/python
## BacLog Copyright 2012 by Timothy Middelkoop licensed under the Apache License 2.0
## Experiment code.

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
        
        ## Setup Metadata
        db.writeTags(objects)
        
        ## Identify tags and set watch to enabled 
        o20=objects.getTag('point',20).single()
        o21=objects.getTag('point',21).single()
        db.enablePoints([o20,o21])
        
        ## Schedule object.
        t=db.now()
        
        if True:
            db.scheduleObject(o20, t+1 , 2, 1)
            db.scheduleObject(o20, t+4 , 1, 1)
            db.scheduleObject(o20, t+7 , 1, 1)
            db.scheduleObject(o20, t+6 , 3, 1)
            
            db.scheduleObject(o21, t+2 , 5, 1)
        
        db.close()
        
        ## Monitor section
        
        

## entry point
if __name__=='__main__':
    Experiment().run()
