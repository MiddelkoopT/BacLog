-- Tags

-- join objects on nn

INSERT INTO PointObjectMap (pointID,objectID,name)
SELECT Points.pointID,Objects.objectID,Points.value
FROM Objects 
JOIN Tags ON (Objects.objectID=Tags.objectID AND tag='nn')
JOIN Points ON (Tags.value=Points.value AND Points.tag='nn')


-- Find errors
SELECT pointid,objectid,pointobjectmap.name,objects.name FROM
(select pointid,count(objectid) from pointobjectmap group by pointid having count(objectid) !=2) AS found
join pointobjectmap using (pointid)
join objects using (objectid)
ORDER BY found.pointID

