-- BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
-- Database Schema

-- BACnet device at the time of use (IP devices)
DROP TABLE IF EXISTS Devices;
CREATE TABLE Devices (
	deviceID SERIAL, 			-- Internal device ID
	IP inet,
	port integer,
	network integer, 			-- BACnet network number (should be the same)
	device integer, 			-- device instance (unique to network)
	name varchar, 				-- device description
	first timestamp,	 		-- first seen
	last timestamp, 			-- valid until (NULL indicates live object)
	CONSTRAINT Devices_PK PRIMARY KEY (deviceID)
);

-- Points.  Physical equipment maped to an object a point in time.
DROP TABLE IF EXISTS Points;
CREATE TABLE Points ( 
	pointID SERIAL, 			-- Internal point ID
	name varchar, 				-- Full point name
	building char(32), 			-- Building Name
	room char(32), 				-- Room number/location
	unit char(32), 				-- Sensor, actuator, or device name/number
	description varchar, 		-- Description example: ROOM TEMP
	first timestamp, 			-- first seen
	last timestamp, 			-- valid until (NULL indicates live point)
	CONSTRAINT Points_PK PRIMARY KEY (pointID)
);

-- BACnet points at the time of use.
DROP TABLE IF EXISTS Objects;
CREATE TABLE Objects (
	objectID SERIAL, 			-- object ID - object definition (temporal)
	deviceID integer, 			-- device ID - device definition (temporal)
	pointID integer, 			-- point ID - physical point definition
	instance integer, 			-- BACnet objectInstance
	type integer, 				-- BACnet objectType
	name varchar,		      	-- BACnet objectName
	description varchar,		-- BACnet description
	first timestamp, 			-- first time seen, valid until last
	last timestamp, 			-- last time seen (NULL indicates live object)
	CONSTRAINT Objects_PK PRIMARY KEY (objectID)
);

-- Log Data
DROP TABLE IF EXISTS Log;
CREATE TABLE Log (
	time timestamp, 			-- time measurement occured.
	IP inet, 					-- remote IP
	port integer, 				-- remote port
	instance integer,	 		-- remote object instance
	objectID integer, 			-- objectID (post processed)
	status integer, 			-- what happened COV/ERROR etc.
	value real 					-- recorded value
);


-- Sample Data/Test
--INSERT INTO Devices 
--	(IP,port,instance,first) 
--VALUES 
--	('192.168.83.100',47808,9001,NOW());
