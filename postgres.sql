-- BacLog Copyright 2010-2012 by Timothy Middelkoop licensed under the Apache License 2.0
-- Database Schema v4

-- BACnet device at the time of use (IP devices)
DROP TABLE IF EXISTS Devices;
CREATE TABLE Devices (
	deviceID SERIAL, 					-- Internal device ID
	IP inet,
	port integer,
	network integer, 					-- BACnet network number (should be the same)
	device integer, 					-- device instance (unique to network)
	name varchar, 						-- device description
	first timestamp with time zone,	 	-- first seen
	last timestamp  with time zone, 	-- valid until (NULL indicates live object)
	CONSTRAINT Devices_PK PRIMARY KEY (deviceID)
);
CREATE INDEX i_Devices_IP_Port ON Devices (IP,port);
CREATE INDEX i_Devices_device ON Devices (device);
CREATE INDEX i_Devices_first ON Devices (first);
CREATE INDEX i_Devices_last ON Devices (last);


-- Points.  Physical equipment maped to an object a point in time.
DROP TABLE IF EXISTS Points;
CREATE TABLE Points ( 
	pointID SERIAL, 					-- Internal point ID
	campus char(8),						-- Campus identifier
	building integer, 					-- Building Number
	first timestamp with time zone, 	-- first seen
	last timestamp  with time zone, 	-- valid until (NULL indicates live point)
	CONSTRAINT Points_PK PRIMARY KEY (pointID)
);

DROP TABLE IF EXISTS Tags;
CREATE TABLE Tags (
	objectID integer,
	tag char(8),
	value varchar,
	CONSTRAINT Tags_PK PRIMARY KEY (objectID,tag)
);

-- BACnet points at the time of use.
DROP TABLE IF EXISTS Objects;
CREATE TABLE Objects (
	objectID SERIAL, 					-- object ID - object definition (temporal)
	deviceID integer, 					-- device ID - device definition (temporal)
	pointID integer, 					-- point ID - physical point definition
	type integer, 						-- BACnet objectType
	instance integer, 					-- BACnet objectInstance
	name varchar,		      			-- BACnet objectName
	description varchar,				-- BACnet description
	first timestamp with time zone, 	-- first time seen, valid until last
	last timestamp  with time zone, 	-- last time seen (NULL indicates live object)
	CONSTRAINT Objects_PK PRIMARY KEY (objectID)
);
CREATE INDEX i_Objects_pointID ON Objects (pointID);
CREATE INDEX i_Objects_deviceID ON Objects (deviceID);
CREATE INDEX i_Objects_device_type_instance ON Objects (deviceID,type,instance);


-- Log Data
DROP TABLE IF EXISTS Log;
CREATE TABLE Log (
	time timestamp with time zone,		-- time measurement occured.
	IP inet, 							-- remote IP
	port integer,		 				-- remote port
	objectID integer, 					-- objectID
	type integer,						-- remote object type
	instance integer,			 		-- remote object instance
	status integer, 					-- what happened COV/ERROR etc.
	value real 							-- recorded value
);
CREATE INDEX i_Log_time ON Log (time);
CREATE INDEX i_Log_objectID ON Log (objectID);


-- Saftey/Enable table (BacLog)
DROP TABLE IF EXISTS Watches;
CREATE TABLE Watches (
	objectID integer,
	stop_low real,
	warn_low real,
	warn_high real,
	stop_high real,
	enabled boolean,					-- Point can be commanded, released otherwise
	warning boolean,					-- Point is in warn range.
	stopped boolean,					-- Point has errored out and point released.
	CONSTRAINT Watches_PK PRIMARY KEY (objectID)
);


-- BacSet Tables


-- Schedule program (Bacset side)
DROP TABLE IF EXISTS Schedule;
CREATE TABLE Schedule (
	scheduleID SERIAL,					-- schedule ID - order of schedule
	objectID integer,					-- object/device to control
	active timestamp with time zone,	-- set value after this time
	until timestamp with time zone,		-- do not set after this value
	value real,							-- set to value
	CONSTRAINT Schedule_PK PRIMARY KEY (scheduleID)
);

-- Control plan (baclog side, refactored/duplicated)
DROP TABLE IF EXISTS Control;
CREATE TABLE Control (
	scheduleID integer,					-- Control based on this schedule
	objectID integer,					-- object to be controled
	active timestamp with time zone,	-- control start
	until timestamp with time zone,		-- control end
	value integer,						-- control value
	enable boolean,						-- control active
	disable boolean,					-- control overriden or released
	CONSTRAINT Control_PK PRIMARY KEY (scheduleID)
);

-- Command Log -- commands written to device.
DROP TABLE IF EXISTS Commands;
CREATE TABLE Commands (
	commandID SERIAL,					-- command handle for updates.
	scheduleID integer, 				-- commanded due to schedule
	time timestamp with time zone,		-- commanded time
	IP inet, 							-- remote IP
	port integer,		 				-- remote port
	device integer,						-- remote device
	type integer,						-- remote object type
	instance integer,			 		-- remote object instance
	value real,							-- commanded value, NULL means release value
	priority integer,					-- priority of commanded value
	success boolean,					-- unit returned success
	verified boolean,					-- True if unit is at commanded value, NULL indicates no attempt.
	CONSTRAINT Command_PK PRIMARY KEY (commandID)
);
CREATE INDEX i_Commands_time ON Commands (time);

