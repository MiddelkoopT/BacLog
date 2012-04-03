#!/usr/bin/python
## BacLog Copyright 2012 by Timothy Middelkoop licensed under the Apache License 2.0
## Experiment code.

from data import Database
import buildings

debug=True
trace=False


class Experiment:

    def runTest(self):
        print "Experiment.runTest>"
        
        ## main objects
        db=Database()
        objects=db.getObjects()
        building=buildings.Test()
        building.tag(objects)
        #building.check(objects)

        ## Identify tags and set watch to enabled 
        o19=objects.getTag('point',19).single()
        o20=objects.getTag('point',20).single()
        o21=objects.getTag('point',21).single()
        test=[o19,o20,o21]
        db.enablePoints(test)
        
        ## Schedule object.
        t=db.now()
#        db.scheduleObject(o19, t+1, 3, 51)
        
#        db.scheduleObject(o20, t+1 , 2, 1)
#        db.scheduleObject(o20, t+4 , 1, 1)
#        db.scheduleObject(o20, t+7 , 1, 1)
#        db.scheduleObject(o20, t+6 , 3, 1)
#        
        db.scheduleObject(o21, t+1 , 10, 1)
        db.scheduleObject(o21, t+3 , 5, None)

        db.close()

    def runPughHall(self):
        print "Experiment.runPughHall>"
        
        ## main objects
        db=Database()
        objects=db.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)

        ## Identify tags and set watch to enabled 
        rooms=objects.getTag('room',['104','105'])
        print rooms
        db.enablePoints(rooms)
        
        ## Schedule object.
#        t=db.now()
        
#        db.scheduleObject(o20, t+1 , 2, 1)
#        db.scheduleObject(o20, t+4 , 1, 1)
#        db.scheduleObject(o20, t+7 , 1, 1)
#        db.scheduleObject(o20, t+6 , 3, 1)
#        
#        db.scheduleObject(o21, t+2 , 5, 1)
        

        db.close()
        

## entry point
if __name__=='__main__':
    Experiment().runTest()
