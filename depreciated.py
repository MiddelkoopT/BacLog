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

## Basic PDU types

class ConfirmedRequest(Packet):
    def __init__(self,service,pid=None):
        global LastRequestID
        Packet.__init__(self,0x04,0x00)                 # Expecting Reply ; Confirmed Request | Unsegmented
        self._add('segment','B',0x04)                   # Maximum APDU size 1024
        self._add('pid','B',pid)                        # Request ID
        self._add('servicechoice','B',
                  service._servicechoice)               # serviceChoice/ACK [no tag]
        self._service=service

        if pid==None:
            LastRequestID+=1
            self.pid=LastRequestID

class UnconfirmedRequest(Packet):
    def __init__(self,service=None,data=None):
        global LastRequestID
        Packet.__init__(self,0x00,0x10)                 # Not Expecting Reply ; Unconfirmed Request | Unsegmented
        self._add('servicechoice','B',  
                  service and service._servicechoice)   # serviceChoice/ACK [no tag]
        self._service=service
        
        if(data):
            self._decode(data)

class ComplexACK(Packet):
    def __init__(self,request=None,data=None):
        Packet.__init__(self,0x00,0x30)                 # Reply ; ComplexACK | Unsegmented
        self._add('pid','B',None)                       # Responding to Request ID
        self._add('servicechoice','B',
                  request and request._servicechoice)   # serviceChoice/ACK
        if(data):
            self._decode(data)

class SimpleACK(Packet):
    def __init__(self,request=None,data=None):
        Packet.__init__(self,0x00,0x20)                 # Reply Present ; SimpleACK | 0x00
        self._add('pid','B',request and request.pid)    # original request ID
        self._add('servicechoice','B',
                  request and request._servicechoice)   # serviceChoice/ACK
        if(data):
            self._decode(data)

