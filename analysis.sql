-- BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
-- Analysis queries.


SELECT * FROM Devices;
SELECT * FROM Objects JOIN Devices USING (deviceID);

SELECT 
	Log.time,Devices.device,Devices.name,
    Objects.type,Objects.instance,Log.value,Objects.name,Objects.description
FROM 
    Log JOIN Devices USING (IP) JOIN Objects USING (deviceID,type,instance);

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
