#!/usr/bin/python
## BacLog Copyright 2012 by Timothy Middelkoop licensed under the Apache License 2.0
## Experiment code.

from data import Database
import buildings

debug=True
trace=False

## psql baclog < postgres.sql; zcat ../data/mtim-baclog-pughhall-v4-bootstrap-2.sql.gz |psql baclog

class Tag:

    def run(self):
        print "Tag.run>"
        
        ## main objects
        db=Database(database='mtim',port=5432)
        
        ## Series 1
        for d in [1,2,3,4]:
            objects=db.getObjects(where="Devices.deviceID=%s" % d)
            building=buildings.PughHall()
            building.tag(objects)
            building.check(objects)
        
            ## Setup Metadata
            db.writeTags(objects)
            building.points(objects)
            db.writePoints(objects)
            
        ## Series 2
        for d in [5,6,7,8]:
            objects=db.getObjects(where="Devices.deviceID=%s" % d)
            building=buildings.PughHall()
            building.tag(objects)
            building.check(objects)
        
            ## Setup Metadata
            db.writeTags(objects)
            
        ## Join on nn
        db.execute("DELETE FROM PointObjectMap")
        db.execute(
"""
INSERT INTO PointObjectMap (pointID,objectID,name)
SELECT Points.pointID,Objects.objectID,Points.value
FROM Objects 
JOIN Tags ON (Objects.objectID=Tags.objectID AND tag='nn')
JOIN Points ON (Tags.value=Points.value AND Points.tag='nn')
"""
        )

        db.close()
        
        ## Join
        

## entry point
if __name__=='__main__':
    Tag().run()
