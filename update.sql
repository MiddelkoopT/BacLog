-- Update objectID w/ device
UPDATE Objects SET device=Devices.device FROM Devices WHERE Objects.deviceID=Devices.deviceID;

-- Update objectID w/ index in log for faster searches. (5433)

-- Join and index object information for performance
DROP TABLE IF EXISTS obj;
SELECT objectID,IP,port,device,type,instance,Devices.first,Devices.last
INTO TABLE obj
FROM Objects
JOIN Devices USING (deviceID);

CREATE INDEX t_obj_objectid ON obj (objectID);
CREATE INDEX t_obj_ip_port ON obj (IP,port);
CREATE INDEX t_obj_type_instance ON obj (type,instance);
CREATE INDEX t_obj_ip_type_instance ON obj (IP,type,instance);
CREATE INDEX t_obj_first ON obj (first);
CREATE INDEX t_obj_last ON obj (last);

-- Do not update in one transaction; start < time <= finish
DROP TABLE IF EXISTS progress;
CREATE TABLE progress (
       start timestamp with time zone,
       finish timestamp with time zone PRIMARY KEY,
       done boolean
);


-- First Job
INSERT INTO progress (finish,done) VALUES (
       (SELECT date_trunc('day',MIN(time)) FROM Log),
       True);


BEGIN;

-- Insert Job
INSERT INTO progress (start,finish,done) VALUES (
       (SELECT MAX(finish) FROM progress),
       (SELECT MAX(finish) FROM progress) + INTERVAL '1 day',
       False
);

-- Job
-- EXPLAIN ANALYZE
UPDATE Log SET objectID=(
       SELECT objectID FROM obj
       WHERE ( obj.IP=Log.IP AND obj.type=Log.type AND obj.instance=Log.instance )
       AND ( Log.time > obj.first AND (Log.time <= obj.last OR obj.last IS NULL) )
)
WHERE time>=(SELECT MIN(start)  FROM progress WHERE done=False) AND
      time< (SELECT MIN(finish) FROM progress WHERE done=False);

-- Finish Job
UPDATE progress SET done=True WHERE finish=(
       SELECT MIN(finish) FROM progress WHERE done=False);

END;


-- Monitor
SELECT * FROM progress ORDER BY finish;


-- TEST
SELECT l.time,objectID,Devices.first,Devices.last
FROM (
       SELECT * FROM Log 
       WHERE time>=(SELECT MIN(start)  FROM progress WHERE done=False)
       AND time< (SELECT MIN(finish) FROM progress WHERE done=False) LIMIT 100) l
JOIN Objects USING (objectID)
JOIN Devices USING (deviceID)
WHERE NOT (l.time>Devices.first AND l.time<=Devices.last);

