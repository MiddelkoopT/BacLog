-- BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
-- Analysis queries.

-- psql -A -F, -c "

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

-- Shows active data points
SELECT
	COUNT(*) AS count,
	device,type,instance,objects.name,objects.description
FROM 
	Log
	JOIN Devices USING (IP,port)
	JOIN Objects USING (deviceID,instance,type)
WHERE
	objects.name LIKE '%241%'
GROUP BY
	device,type,instance,objects.name,objects.description
ORDER BY count DESC

-- Find Data
SELECT value 
FROM Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance) 
WHERE device=9040 AND type=0 AND instance=3
