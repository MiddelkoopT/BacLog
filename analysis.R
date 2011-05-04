## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis

library('lattice');

library('RODBC');
c <- odbcConnect('PostgreSQL');

## Meta information
d <- 
  	sqlQuery(c,'SELECT device,name	FROM Devices;');
o <- 
 	sqlQuery(c,"SELECT device,instance,type,objects.name,objects.description
 	FROM Objects JOIN Devices USING (deviceID) 
	-- WHERE objects.name LIKE '%ROOM TEMP%'
	")

tn <- sqlQuery(c,'SELECT MIN(time) FROM LOG;');
tm <- sqlQuery(c,'SELECT MAX(time) FROM LOG;');
c(tn,tm)

## Graph point
s <- sqlQuery(c,"SELECT time,value FROM Log JOIN Devices USING (IP,port) WHERE
    time > TIMESTAMP '2011-04-29 09:00-04' AND
    time < TIMESTAMP '2011-04-30 15:00-04' AND
	device=9040 AND type=0 AND instance=3
	ORDER BY time;")
xyplot(value~time,s,type='o')

## Graph multiple points
s2 <- sqlQuery(c,"SELECT time,value,instance FROM Log JOIN Devices USING (IP,port) WHERE
--				time > TIMESTAMP '2011-04-29 09:00-04' AND
--				time < TIMESTAMP '2011-04-29 15:00-04' AND
				(
				    (device=9040 AND type=0 AND instance=12404) 
				 OR (device=9040 AND type=1 AND instance=12478)
				)
				ORDER BY time;")
xyplot(value~time,s2,group=instance,type='o')

## Dump database
l <- sqlQuery(c,'
SELECT 
	Log.time,Devices.device,Devices.name,
    Objects.type,Objects.instance,Log.value,Objects.name,Objects.description
FROM 
    Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance);
');

