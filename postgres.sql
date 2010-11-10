-- BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
-- Database Schema

-- BACnet device at the time of use (IP devices)
DROP TABLE IF EXISTS Devices;
CREATE TABLE Devices (
	device SERIAL , -- device ID
	IP inet,
	port integer,
	network integer, -- BACnet network number (should be the same)
	instance integer, -- device instance (unique to network)
	first timestamp, -- first seen
	last timestamp, -- valid until (NULL indicates live object)
	CONSTRAINT Devices_PK PRIMARY KEY (device)
);

-- Points.  Physical equipment maped to an object a point in time.
-- CREATE TABLE Points ( point integer -- Internal point ID );

-- BACnet points at the time of use.
DROP TABLE IF EXISTS Objects;
CREATE TABLE Objects (
	object SERIAL, -- object ID; object definition (temporal)
	device integer, -- device ID; device definition (temporal)
	point integer, -- point ID; physical point definition
	instance integer, -- object instance
	type integer, -- BACnet ObjectType
	first timestamp, -- first time seen, valid until last
	last timestamp, -- last time seen (NULL indicates live object)
	CONSTRAINT Objects_PK PRIMARY KEY (object)
);

-- Log Data
DROP TABLE IF EXISTS Log;
CREATE TABLE Log (
	object integer, -- object ID from Objects
	time timestamp, -- time measurement occured.
	status integer, -- what happened COV/ERROR etc.
	value real -- recorded value
);


-- Sample Data/Test
INSERT INTO Devices 
	(IP,port,instance,first) 
VALUES 
	('192.168.83.100',47808,9001,NOW());
