#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Database Driver

import psycopg2

class Database:
    def __init__(self,database='baclog'):
        self.conn = psycopg2.connect(database=database)

    def getDevices(self):
        cur=self.conn.cursor()
        cur.execute("SELECT device,IP,port FROM Devices WHERE last IS NULL")
        return cur.fetchall()

       