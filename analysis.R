## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis

library('lattice');

library('RODBC');
c <- odbcConnect('PostgreSQL');

d <- sqlQuery(c,'SELECT device,name	FROM Devices;');
o <- sqlQuery(c,"SELECT device,instance,type,objects.name FROM Objects JOIN Devices USING (deviceID) WHERE objects.name like '%TEMP%';")
o
s <- sqlQuery(c,"SELECT time,value FROM Log JOIN Devices USING (IP,port) WHERE 
	device=9041 AND instance=3 AND type=0")
s
xyplot(value~time,s,type='l')

l <- sqlQuery(c,'
SELECT 
	Log.time,Devices.device,Devices.name,
    Objects.type,Objects.instance,Log.value,Objects.name,Objects.description
FROM 
    Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,instance);
');
