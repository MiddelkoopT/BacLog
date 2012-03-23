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
        db=Database()
        
        ## populate meta information
        objects=db.getObjects()
        building=buildings.PughHall()
        building.tag(objects)
        building.check(objects)
        
        ## Setup Metadata
        db.writeTags(objects)

        db.close()
        

## entry point
if __name__=='__main__':
    Tag().run()
