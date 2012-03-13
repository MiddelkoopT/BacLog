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
        building=buildings.PughHall()
        building.tag(objects)
        #building.check(objects)
        
        zone=objects.getTag('zone',1) ## All zone objects (VAV and AHU)
        temp=zone.getTag('descriptor','CTL STPT')
        
        control=temp.getTag('space','TRO1A')
        
        for o in control:
            print o.tags;

        print control


## entry point
if __name__=='__main__':
    Experiment().run()
