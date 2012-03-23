## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Common Objects

import tagged

class Device:
    '''
    Device Object
    @ivar objects: Object 
    '''
    objects=None
    def __init__(self,IP,port,device,deviceID=None):
        self.id=deviceID
        self.IP=IP
        self.port=port
        self.address=(IP,port)
        self.device=device
        self.objects=[]
        
    def __repr__(self):
        return "{Device@%s(%s,%s,%s)}" % (self.id or '',self.IP,self.port,self.device)
    
class Object:
    def __init__(self,deviceID,objectID,otype,oinstance,name):
        self.deviceID=deviceID
        self.id=objectID
        self.type=otype
        self.instance=oinstance
        self.objectIdentifier=tagged.ObjectIdentifier(otype,oinstance)
        self.name=name
        self.enabled=False

    def __repr__(self):
        return "{Object@%s(%d,%d)|%s|" % (self.id or '',self.type,self.instance,self.name)