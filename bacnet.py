## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import tagged

from tagged import Unsigned32, Unsigned16, Unsigned, Boolean, String, ObjectIdentifier, Property, Enumerated, Bitstring, Sequence, SequenceOf, Array, Tagged

## Data types
class ObjectIdentifierArray(Array):
    _type=tagged.ObjectIdentifier

## PhaseII Enumerations

class PropertyIdentifier(Enumerated):
    _enumeration={
                  'presentValue':85,
                  'objectIdentifier':75,
                  'objectList':76,
                  'objectName':77,
                  'notificationClass':17,
                  'statusFlags':111,
                  'protocolServicesSupported':97,
                  'systemStatus':112,
                  'vendorIdentifier':120,
                  'maxAPDU':62,
                  'maxSegments':167,
                  'segmentation':107,
                  'APDUSegmentationTimeout':10,
                  'APDUTimeout':11,
                  'APDURetries':73,
                  }
    
class ServicesSupported(Bitstring):
    _size=40
    _field={
            'readProperty':12,
            'readPropertyMultiple':14,
            'unconfirmedCOVNotification':28,
            'whoIs':34,
            }

class ObjectType(Enumerated):
    _enumeration={
                  'analogValue':2,
                  'binaryInput':3,
                  'binaryOutput':4,
                  'device':8,
                  'file':10,
                  }

class Segmented(Enumerated): # BACnetSegmentation
    _enumeration={
                  'noSegmentation':3,
                  }

class DeviceStatus(Enumerated): # BACnetDeviceStatus
    _enumeration={
                  'operational':0,
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

class WhoIs(UnconfirmedServiceRequest):
    _servicechoice=8 # who-Is
    _sequence=[
               ('low',Unsigned32),    # [0] deviceInstanceRangeLowLimit
               ('high',Unsigned32),   # [1] deviceInstanceRangeHighLimit
               ]
    
class IAm(UnconfirmedServiceRequest):
    _servicechoice=0 # i-Am
    _context=False # context values not used.
    _sequence=[
               ('object',ObjectIdentifier), # iAmDeviceIdentifier
               ('maxlength',Unsigned),      # maxADPULengthAccepted
               ('segmentation',Segmented),  # segmentationSupported
               ('vendor',Unsigned16),       # vendorID
               ]

class ReadProperty(ConfirmedServiceRequest):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0] objectIdentifier
               ('property',PropertyIdentifier), # [1] propertyIdentifier
               ('index',Unsigned),              # [2] propertyArrayIndex OPTIONAL
               ]
    def _set(self,property=None,object=None,objectInstance=None):
        '''ReadProperty convience constructor'''
        if property!=None and object!=None:
            self.property=PropertyIdentifier(property)
            if objectInstance!=None:
                object=ObjectIdentifier(object,objectInstance)
            self.object=object

class PropertyReference(Sequence):
    _sequence=[
               ('property',PropertyIdentifier),     # [0] propertyIdentifier
               ('index',Unsigned),                  # [1] propertyArrayIndex OPTIONAL
               ]

class SequenceOfPropertyReference(SequenceOf):
    _sequenceof=PropertyReference

class ReadAccessSpecification(Sequence):
    _sequence=[
               ('object',ObjectIdentifier),             # [0] objectIdentifier
               ('list',SequenceOfPropertyReference)     # [1] listOfProperties
               ]

class ReadAccessResult_Result(Sequence):
    _sequencestart=2
    _sequence=[
               ('property',PropertyIdentifier),         # [2] propertyIdentifier
               ('index',Unsigned),                      # [3] propertyArrayIndex OPTIONAL
               ('value',Property),                      # [4] CHOICE: propertyValue ANS.1 
#               ('error',Error),                        # [5]         propertyError
               ]

class SequenceOfReadAccessResult_Result(SequenceOf):
    _sequenceof=ReadAccessResult_Result
    _sequencekey=2

class ReadAccessResult(Sequence):
    _sequence=[
               ('object',ObjectIdentifier),                     # [0] objectIdentifier
               ('list',SequenceOfReadAccessResult_Result),      # [1] listOfResults ANONYMOUS SEQUENCE OF SEQUENCE
                                                                # [2-5] ReadAccessResult_Result
               ]
    
class ReadPropertyMultiple(SequenceOf,ConfirmedServiceRequest):
    _servicechoice=14 # readPropertyMutiple
    _sequenceof=ReadAccessSpecification # SequenceOf

class ReadPropertyResponse(ConfirmedServiceACK):
    _servicechoice=12 # readProperty
    _sequence=[
               ('object',ObjectIdentifier),     # [0] objectIdentifer
               ('property',PropertyIdentifier), # [1] propertyIdentifier
               ('index',Unsigned),              # [2] propertyArrayIndex OPTIONAL
               ('value',Property),              # [3] propertyValue ASN.1
               ]

class ReadPropertyMultipleResponse(SequenceOf,ConfirmedServiceACK):
    _servicechoice=14 # readPropertyMultiple
    _sequenceof=ReadAccessResult # SequenceOf

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
             'objectName':String,
             'objectIdentifier':ObjectIdentifier,
             'protocolServicesSupported':ServicesSupported,
             'systemStatus':DeviceStatus,
             'vendorIdentifier':Unsigned16,
             'maxAPDU':Unsigned,
             'maxSegments':Unsigned,
             'segmentation':Segmented,
             'APDUSegmentationTimeout':Unsigned,
             'APDUTimeout':Unsigned,
             'APDURetries':Unsigned,
             }


## Create generated classes/dictionaries
ConfirmedServiceChoice=tagged.buildServiceChoice(ConfirmedServiceRequest,vars()) 
ConfirmedServiceResponseChoice=tagged.buildServiceChoice(ConfirmedServiceACK,vars()) 
UnconfirmedServiceChoice=tagged.buildServiceChoice(UnconfirmedServiceRequest,vars()) 

## Idexed by PDU type
ServiceChoice=[ConfirmedServiceChoice,UnconfirmedServiceChoice]

## Generate derived attributes.
tagged.buildProperty(PropertyMap)
tagged.buildDisplay(vars())
tagged.buildEnumeration(vars())
