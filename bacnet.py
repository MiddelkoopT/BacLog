## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

from tagged import *

## PhaseII data types
class PropertyIdentifier(Enumerated):
    ## TODO: Remove/Merge BACnetPropertyIdentifier
    _enumeration={
                  'presentValue':85,
                  'objectList':76,
                  'notificationClass':17,
                  'statusFlags':111
                  }
    _display=dict((value, key) for key, value in _enumeration.iteritems())
        
class PropertyValue(Sequence):
    _sequence=[
               ('property',PropertyIdentifier),         # [0] propertyIdentifier
               ('index',Unsigned),                      # [1] propertyArrayIndex OPTIONAL
               ('value',Application),                   # [2] value ASN.1
               ('priority',Unsigned),                   # [3] priority OPTIONAL
               ]

class SequenceOfPropertyValue(SequenceOf):
    _sequenceof=PropertyValue
    _sequencekey=0

## PhaseII PDU packets
class COVNotification(Sequence): # SEQUENCE
    _sequence=[
               ('pid',Unsigned32),                      # [0] subscriberProcessIdentifier
               ('device',ObjectIdentifier),             # [1] initiatingDeviceIdentifier
               ('object',ObjectIdentifier),             # [2] monitoredObjectIdentifer
               ('time',Unsigned),                       # [3] timeRemaining
               ('values',SequenceOfPropertyValue),      # [4] listOfValues
               ]
    
class ConfirmedCOVNotification(COVNotification):
    pass
class UnconfirmedCOVNotification(COVNotification):
    pass

class ServiceRequest(Tagged):
    pass

class SubscribeCOV(ServiceRequest):
    _servicechoice=''
    _sequence=[
               ('pid',Unsigned32),              # [0] subscriberProcessIdentifier
               ('object',ObjectIdentifier),     # [1] monitoredObjectIdentifier
               ('confirmed',Boolean),           # [2] issueConfirmedNotifications
               ('lifetime',Unsigned),           # [3] lifetime
               ]
    
## PDU Requests
BACnetConfirmedService =  { ConfirmedCOVNotification:1 } 
BACnetUnconfirmedService =  { UnconfirmedCOVNotification:2 } 
