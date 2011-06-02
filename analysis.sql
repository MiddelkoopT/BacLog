-- BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
-- Analysis queries.

-- psql -q -A -F',' -P footer=off -c "

-- Metadata
SELECT * FROM Devices;
SELECT * FROM Objects JOIN Devices USING (deviceID);

-- Dump database
SELECT 
	Log.time,Devices.device, -- Devices.name,
    Objects.type,Objects.instance,Objects.name, -- Objects.description,
    Log.value
FROM 
    Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance);

-- Dump database into a intermedary table
DROP TABLE IF EXISTS Data;
SELECT 
    time,device,type,instance,value 
INTO Data
FROM 
    Log JOIN Devices USING(IP,port) JOIN Objects USING (deviceID,type,instance)
WHERE
    device=9040 AND instance/100=124
ORDER BY time
LIMIT 100000;

CREATE INDEX i_Data_time ON Data (time);

SELECT * FROM Data;

------
-- Analysis

-- Shows active data points
SELECT
	COUNT(*) AS count,
	device,type,instance,objects.name,objects.description
FROM 
	Log
	JOIN Devices USING (IP,port)
	JOIN Objects USING (deviceID,instance,type)
GROUP BY
	device,type,instance,objects.name,objects.description
ORDER BY count DESC

-- Find Data
SELECT DISTINCT value 
FROM Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance) 
WHERE device=9040 AND type=1 AND instance=14834

-- Find parameters on bus.
SELECT DISTINCT device,type,instance,objects.name, value 
FROM Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance) 
WHERE objects.name LIKE '%VAV%' AND MOD(instance,100)=77
ORDER BY objects.name

-- Look at VAV
SELECT DISTINCT instance, Objects.name, MIN(value), MAX(value), AVG(value), COUNT(value)
FROM Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance) 
WHERE device=9040 AND instance>=12400 AND instance <=12499
GROUP BY instance, Objects.name
ORDER BY instance

-- Multiple data points
SELECT time,value,instance FROM Log JOIN Devices USING (IP,port) 
WHERE
				time > TIMESTAMP '2011-05-06 15:00-04' AND
				time < TIMESTAMP '2011-05-06 16:00-04' AND
				(
				    (device=9040 AND type=4 AND instance=14805) 
				 OR (device=9040 AND type=1 AND instance=14875)
				 OR (device=9040 AND type=1 AND instance=14877)
				)
ORDER BY time;

