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
        return response
    
    def close(self):
        self.cursor.close() ## accesses FD
        

class DatabaseHandler:
    """Database IO handler for scheduler class"""
    POLL_OK=psycopg2.extensions.POLL_OK         # 0
    POLL_READ=psycopg2.extensions.POLL_READ     # 1
    POLL_WRITE=psycopg2.extensions.POLL_WRITE   # 2
    POLL_ERROR=psycopg2.extensions.POLL_ERROR   # 3
    IDLE,EXECUTE,FETCH,CLOSE = range(4)
    
    def __init__(self,database='baclog'):
        if trace: print "DatabaseHandler>", database
        
        ## Handler API]
        self.send=False
        self.recv=False

        ## Database
        self.conn=psycopg2.connect(database=database,async=1)
        psycopg2.extras.wait_select(self.conn) ## Block; connections are expensive anyways.
        self.socket=self.conn.fileno()

        ## Internal state
        self.state=self.IDLE
        self.work=None   ## current work
        
        Query._handler=Query._handler or self ## default handler
        
    ## internal shortcut.
    def query(self,query,*args):
        return Query(self,query,*args)
        
    ## Handler API
        
    def put(self,work):
        if debug: print "DatabaseHandler.put>", work.tid, work.request.query
        assert not self.send ## Database can only handle one simultaneous query.
        self.send=True
        self.work=work
        self.work.request.execute()
        self.state=DatabaseHandler.EXECUTE ## Excuting

    def reading(self):
        return self.conn.poll()==self.POLL_READ

    def writing(self):
        return self.conn.poll()==self.POLL_WRITE
    
    def ready(self):
        if self.state==self.IDLE:
            return False
        return self.conn.poll()==self.POLL_OK

    def process(self):
        if trace: print "DatabaseHandler.process>", self.state
        assert self.conn.poll()==self.POLL_OK
        assert not self.conn.isexecuting()

        ## State machine.
        if self.state==DatabaseHandler.EXECUTE:
            self.work.response=self.work.request.fetch()
            self.state=DatabaseHandler.FETCH
        elif self.state==DatabaseHandler.FETCH:
            self.work.request.close()
            self.work.request=None
            self.state=DatabaseHandler.CLOSE
        elif self.state==DatabaseHandler.CLOSE:
            self.recv=True ## Data now availabe.
            self.state=DatabaseHandler.IDLE
        
    ## Socket must be in "ready" state before processing (idle)
    def read(self):
        pass
    def write(self):
        pass
        
    def get(self):
        if debug: print "DatabaseHandler.get>", self.work.tid, self.work.response
        assert self.recv
        work=self.work
        self.send=False
        self.recv=False
        self.work=None
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
    
