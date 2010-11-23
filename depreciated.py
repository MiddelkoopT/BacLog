## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
##### PhaseI Packets.

from packet import *

## Specification Enumerations
BACnetObjectType = {'binary-input':3,'binary-output':4, 'device':8}
BACnetPropertyIdentifier = {'present-value':85, 'object-list':76, 'notification-class':17}
BACnetConfirmedServiceChoice = {'readProperty':12, 'subscribeCOV':5 }
BACnetUnconfirmedServiceChoice = {'unconfirmedCOVNotification':2 }

## Used to get a new request ID
LastRequestID = 0

class ConfirmedRequest(Packet):
    def __init__(self,servicechoice,pid=None):
        global LastRequestID
        Packet.__init__(self,0x04,0x00) # Expecting Reply ; Confirmed Request | Unsegmented
        self._add('segment','B',0x04)   # Maximum APDU size 1024
        self._add('pid','B',pid)        # Request ID
        self._add('servicechoice','B',  # serviceChoice/ACK [no tag]
                  BACnetConfirmedServiceChoice[servicechoice])
        if pid==None:
            LastRequestID+=1
            self.pid=LastRequestID

class UnconfirmedRequest(Packet):
    def __init__(self,servicechoice=None,data=None):
        global LastRequestID
        Packet.__init__(self,0x00,0x10) # Not Expecting Reply ; Unconfirmed Request | Unsegmented
        self._add('servicechoice','B',  # serviceChoice/ACK [no tag]
                  servicechoice and BACnetUnconfirmedServiceChoice[servicechoice])
        if(data):
            self._decode(data)

class ComplexACK(Packet):
    def __init__(self,servicechoice=None,data=None):
        Packet.__init__(self,0x00,0x30) # Reply ; ComplexACK | Unsegmented
        ## APDU header
        self._add('pid','B',None)       # Responding to Request ID
        self._add('servicechoice','B',  # serviceChoice/ACK [no tag]
                  servicechoice and BACnetConfirmedServiceChoice[servicechoice])
        if(data):
            self._decode(data)

class SimpleACK(Packet):
    def __init__(self,request=None,data=None):
        Packet.__init__(self,0x00,0x20)                 # Reply Present ; SimpleACK | 0x00
        self._add('pid','B',request and request.pid)    # original request ID
        self._add('servicechoice','B',request and request._servicechoice)  # serviceChoice/ACK
        if(data):
            self(data)

## PDU Payload.

class ReadPropertyRequest(ConfirmedRequest):
    def __init__(self,type,instance,property='present-value'):
        ConfirmedRequest.__init__(self,'readProperty')
        self._addObjectID(type,instance)    # ObjectIdentifier
        self._addPropertyID(property)       # PropertyIdentifier
        #                                   # PropertyArrayIndex (optional)

class ReadPropertyResponse(ComplexACK):
    def __init__(self,request):
        ComplexACK.__init__(self,'readProperty')
        self._addObjectID(request.type,request.instance)    # ObjectIdentifier
        self._addPropertyID(request.property)               # PropertyIdentifier
        self._nextTag()                                     # PropertyArrayIndex (Optional)
        ## PropertyValue
        self._openTag()
        self._Enumerated(None,'value')
        self._closeTag()

class SubscribeCOVRequest(ConfirmedRequest):
    def __init__(self,object,lifetime=120):
        ConfirmedRequest.__init__(self,'subscribeCOV')
        self._addUnsigned32(0)      # subscriberProcessIdentifier
        self._addObjectID(*object)  # monitoredObjectIdentifier
        self._addBoolean(False)     # issueConfirmedNotifications
        self._addUnsigned(lifetime) # lifetime

