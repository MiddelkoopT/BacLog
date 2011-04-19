
### Random development notes

## SQL
SELECT Log.time,Devices.device,Devices.name,Objects.type,Objects.instance,Log.value,Objects.name,Objects.description FROM Log JOIN Devices USING (IP) JOIN Objects USING (deviceID,instance);

select * FROM Log WHERE age(NOW(),time) < interval '00:00:10';
while sleep 1; do psql baclog --tuples-only -c "select * FROM Log WHERE age(NOW(),time) < interval '00:00:01';" ; done

## Development tools
rsync -av *.py baclog.ad.ufl.edu:BacLog/
rsync -a kiwi:uflorida/BacLog/\*.py . && rsync -a *.py baclog.ad.ufl.edu:BacLog/

## Rather permiscuous but works for single user machines.
setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap
Capture filter: udp port 47808
wireshark -k -i <( ssh baclog.ad.ufl.edu /usr/sbin/tcpdump -i eth0 -s 0 -w - port 47808 )

## PXC
Field Panel/FLN/Drop/Point
9001/0/0/1
Enable Point
