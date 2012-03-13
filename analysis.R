## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Analysis

library('lattice');

library('RODBC');
c <- odbcConnect('BacLog');

d <- sqlQuery(c,"
SELECT Log.time,Devices.device,Devices.name,Objects.type,Objects.instance,Log.value,Objects.name 
FROM Log JOIN Devices USING (IP,port) 
JOIN Objects USING (deviceID,type,instance) 
WHERE Devices.last IS NULL
AND device=9040 AND type=0 AND instance=1
-- AND age(NOW(),time) < interval '00:01:30'
")

xyplot(value~time,d,type='l')


#### Historical.


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
--	time > TIMESTAMP '2011-05-05 00:30-04' AND
--	time < TIMESTAMP '2011-05-05 01:30-04' AND
	device=9040 AND instance=12415
	ORDER BY time;")
xyplot(value~time,s,type='o')


max(diff(s$value[-1]) %% 131071)

plot( 
	(diff(s$value[-1]) %% 131071) / as.real(diff(s$time)[-length(s)]) *60 
)


xyplot(pmax(0,diff(value))~time,s,type='l')

pmax(0,diff(s$value))

# extra
xyplot(diff(value)~time,s[1000:1500,],scales=list(y=list(limit=c(0,300))),type='o')
plot(diff(s[1000:5000,]$time),type='l')
hist(diff(s$time),breaks=30)


## Graph multiple points
m <- sqlQuery(c,"SELECT time,value,instance FROM Log JOIN Devices USING (IP,port) WHERE
--				time > TIMESTAMP '2011-04-29 09:00-04' AND
--				time < TIMESTAMP '2011-04-29 15:00-04' AND
				(
				    (device=9040 AND type=1 AND instance=12475) 
				 OR (device=9040 AND type=1 AND instance=14875)
				)
				ORDER BY time;")
xyplot(value~time,m,group=instance,type='o')


## Dump database
l <- sqlQuery(c,'
SELECT 
	Log.time,Devices.device,Devices.name,
    Objects.type,Objects.instance,Log.value,Objects.name,Objects.description
FROM 
    Log JOIN Devices USING (IP,port) JOIN Objects USING (deviceID,type,instance);
');


####

## Analysis of room 241/VAV129/O9040.124xx



