## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import tagged
from tagged import Enumerated, Sequence, SequenceOf, Application, Unsigned32, Unsigned, Boolean, ObjectIdentifier, PropertyArrayIndex

## PhaseII Enumerations

class PropertyIdentifier(Enumerated):
    _enumeration={
                  'presentValue':85,
                  'objectList':76,
                  'notificationClass':17,
                  'statusFlags':111
                  }

class ObjectType(Enumerated):
    _enumeration={
                  'binary-input':3,
                  'binary-output':4,
                  'device':8
                  }

## PhaseII Data types
        
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

class UnconfirmedServiceRequest(Sequence):
    pass

class UnconfirmedCOVNotification(UnconfirmedServiceRequest):
    _servicechoice=2 # unconfirmedCOVNotification
    _sequence=[
               ('pid',Unsigned32),                      # [0] subscriberProcessIdentifier
               ('device',ObjectIdentifier),             # [1] initiatingDeviceIdentifier
               ('object',ObjectIdentifier),             # [2] monitoredObjectIdentifer
               ('time',Unsigned),                       # [3] timeRemaining
               ('values',SequenceOfPropertyValue),      # [4] listOfValues
               ]
    
class ServiceRequest(Sequence):
    pass

class ComplexACK(Sequence):
    pass

class ReadProperty(ServiceRequest):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0] 
               ('property',PropertyIdentifier), # [1] 
               ('index',PropertyArrayIndex),    # [2] OPTIONAL
               ]

class ReadPropertyResponse(ComplexACK):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0]
               ('property',PropertyIdentifier), # [1] 
               ('index',PropertyArrayIndex),    # [2] OPTIONAL
               ('value',Application)            # [3]
               ]

class SubscribeCOV(ServiceRequest):
    _servicechoice=5 # subscribeCOV
    _sequence=[
               ('pid',Unsigned32),              # [0] subscriberProcessIdentifier
               ('object',ObjectIdentifier),     # [1] monitoredObjectIdentifier
               ('confirmed',Boolean),           # [2] issueConfirmedNotifications
               ('lifetime',Unsigned),           # [3] lifetime
               ]

## Create generated classes/dictionaries
ConfirmedServiceChoice=tagged.buildServiceChoice(ServiceRequest,vars()) 
ConfirmedServiceResponseChoice=tagged.buildServiceChoice(ComplexACK,vars()) 
UnconfirmedServiceChoice=tagged.buildServiceChoice(UnconfirmedServiceRequest,vars()) 

## Generate derived attributes.
tagged.buildDisplay(vars())
