## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import tagged

from tagged import Unsigned32, Unsigned, Boolean, ObjectIdentifier, Property, Enumerated, Sequence, SequenceOf, Array, Tagged

## Data types
class ObjectIdentifierArray(Array):
    _type=tagged.ObjectIdentifier

## PhaseII Enumerations

class PropertyIdentifier(Enumerated):
    _enumeration={
                  'presentValue':85,
                  'objectList':76,
                  'notificationClass':17,
                  'statusFlags':111,
                  }

class ObjectType(Enumerated):
    _enumeration={
                  'analogValue':2,
                  'binaryInput':3,
                  'binaryOutput':4,
                  'device':8,
                  'file':10,
                  }

## PhaseII Data types
        
class PropertyValue(Sequence):
    _sequence=[
               ('property',PropertyIdentifier),         # [0] propertyIdentifier
               ('index',Unsigned),                      # [1] propertyArrayIndex OPTIONAL
               ('value',Property),                      # [2] value ASN.1
               ('priority',Unsigned),                   # [3] priority OPTIONAL
               ]

class SequenceOfPropertyValue(SequenceOf):
    _sequenceof=PropertyValue
    _sequencekey=0

## PhaseII PDU packets

class ConfirmedServiceRequest(Sequence):
    _pdutype=0x0 # ConfirmedRequest

class UnconfirmedServiceRequest(Sequence):
    _pdutype=0x1 # UnconfirmedRequest

class SimpleACK(Tagged):
    _pdutype=0x2 # SimpleACK

class ConfirmedServiceACK(Sequence):
    _pdutype=0x3 # ComplexACK

## Services

class UnconfirmedCOVNotification(UnconfirmedServiceRequest):
    _servicechoice=2 # unconfirmedCOVNotification
    _sequence=[
               ('pid',Unsigned32),                      # [0] subscriberProcessIdentifier
               ('device',ObjectIdentifier),             # [1] initiatingDeviceIdentifier
               ('object',ObjectIdentifier),             # [2] monitoredObjectIdentifer
               ('time',Unsigned),                       # [3] timeRemaining
               ('values',SequenceOfPropertyValue),      # [4] listOfValues
               ]

class ReadProperty(ConfirmedServiceRequest):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0] objectIdentifier
               ('property',PropertyIdentifier), # [1] propertyIdentifier
               ('index',Unsigned),              # [2] propertyArrayIndex OPTIONAL
               ]
    def _init(self,property=None,object=None,objectInstance=None):
        '''ReadProperty convience constructor'''
        if property!=None and object!=None:
            self.property=PropertyIdentifier(property)
            if objectInstance!=None:
                object=ObjectIdentifier(object,objectInstance)
            self.object=object

class ReadPropertyResponse(ConfirmedServiceACK):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0] objectIdentifer
               ('property',PropertyIdentifier), # [1] propertyIdentifier
               ('index',Unsigned),              # [2] propertyArrayIndex OPTIONAL
               ('value',Property),              # [3] propertyValue ASN.1
               ]
    #_context={'value':('property','object')} # Hard coded in Sequence.

class SubscribeCOV(ConfirmedServiceRequest):
    _servicechoice=5 # subscribeCOV
    _sequence=[
               ('pid',Unsigned32),              # [0] subscriberProcessIdentifier
               ('object',ObjectIdentifier),     # [1] monitoredObjectIdentifier
               ('confirmed',Boolean),           # [2] issueConfirmedNotifications
               ('lifetime',Unsigned),           # [3] lifetime
               ]

## (property, objectType=None) : DataClass mapping
PropertyMap={
             'objectList':ObjectIdentifierArray,
             }


## Create generated classes/dictionaries
ConfirmedServiceChoice=tagged.buildServiceChoice(ConfirmedServiceRequest,vars()) 
ConfirmedServiceResponseChoice=tagged.buildServiceChoice(ConfirmedServiceACK,vars()) 
UnconfirmedServiceChoice=tagged.buildServiceChoice(UnconfirmedServiceRequest,vars()) 

## Generate derived attributes.
tagged.buildProperty(PropertyMap)
tagged.buildDisplay(vars())
tagged.buildEnumeration(vars())
