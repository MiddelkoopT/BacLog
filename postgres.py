## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Database Driver

import time
import psycopg2.extras
from scheduler import Task


debug=False
trace=False

## Asynchronous interface
    
class Query:
    _handler=None
    cursor=None
    def __init__(self,query,*args):
        self.cursor=None
        self.query=query
        self.param=args
        if debug: print "Query>",query,args #,self._handler
        
    def execute(self):
        conn=self._handler.conn
        if trace: print "Query.execute>", conn.poll()
        self.cursor=conn.cursor()
        self.cursor.execute(self.query,self.param)
        if trace: print "Query.execute>"
        
    def fetch(self):
        if self.cursor.description==None:
            response=self.cursor.rowcount ## Not a query 
        else:
            response=self.cursor.fetchall()
        self.cursor.close()
        return response
        

class DatabaseHandler:
    """Database IO handler for scheduler class"""
    POLL_OK=psycopg2.extensions.POLL_OK         # 0
    POLL_READ=psycopg2.extensions.POLL_READ     # 1
    POLL_WRITE=psycopg2.extensions.POLL_WRITE   # 2
    POLL_ERROR=psycopg2.extensions.POLL_ERROR   # 3
    
    def __init__(self,database='baclog'):
        if trace: print "DatabaseHandler>", database
        self.conn=psycopg2.connect(database=database,async=1)
        psycopg2.extras.wait_select(self.conn) ## Block; connections are expensive anyways.
        self.socket=self.conn.fileno()
        ## Postgresql does not support multiple queries on one connection/fd
        self.send=None
        self.recv=None
        self.wait=None
        Query._handler=Query._handler or self ## default handler
        
    def query(self,query,*args):
        return Query(self,query,*args)
        
    ## Handler API
        
    def put(self,work):
        if debug: print "DatabaseHandler.put>", work.tid, work.request.query
        assert not self.send ## Database can only handle one simultaneous query.
        self.send=work

    def writing(self):
        return self.send!=None or self.conn.poll()==self.POLL_WRITE

    def reading(self):
        return self.wait!=None or self.conn.poll()==self.POLL_READ
        
    def write(self):
        if trace: print "DatabaseHandler.write>", self.send, self.conn.poll(), self.conn.isexecuting()
        if self.conn.isexecuting():
            return
        self.send.request.execute()
        self.wait=self.send
        self.send=None

    def read(self):
        if trace: print "DatabaseHandler.read>", self.conn.poll()
        self.recv=self.wait
        self.wait=None
        
    def get(self):
        if trace: print "DatabaseHandler.get>", self.recv.tid
        work=self.recv
        work.response=work.request.fetch()
        work.request=None
        self.recv=None
        if debug: print "DatabaseHandler.get>", work.tid, work.response
        return work
    
    def shutdown(self):
        self.conn.close()

## Database Tasks

class GetDevices(Task):
    devices=None
    def run(self):
        query=Query("SELECT IP,port,instance FROM Devices WHERE last IS NULL")
        response=yield query
        self.devices=[]
        for IP,port,instance in response:
            self.devices.append(((IP,port),instance))
        print "GetDevices>", self.devices

class Log(Query):
    '''
    Build Log Query
    '''
    def __init__(self,IP,port,instance,value,status=None,objectID=None):
        query="INSERT INTO Log (time,IP,port,instance,value,status,objectID) VALUES (%s,%s,%s,%s,%s,%s,%s);"
        now=psycopg2.TimestampFromTicks(time.time())
        Query.__init__(self,query, now,IP,port,instance,value,status,objectID)

## Synchronous Interface

class Database:
    def __init__(self,database='baclog'):
        self.conn=psycopg2.connect(database=database)
        self.database=database

    def getDevices(self):
        cur=self.conn.cursor()
        cur.execute("SELECT IP,port,instance FROM Devices WHERE last IS NULL")
        devices=[]
        for IP,port,instance in cur.fetchall():
            devices.append(((IP,port),instance))
        cur.close()
        return devices
    
