## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Database Driver

import time
import psycopg2.extras
from scheduler import Task

import object

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
    IDLE,WAIT,EXECUTE,FETCH,CLOSE = range(5)
    
    def __init__(self,database='baclog'):
        if trace: print "DatabaseHandler>", database
        
        ## Handler API
        self.send=[]
        self.recv=[]

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
        if debug: print "DatabaseHandler.put>", len(self.send), work.tid, work.request.query
        if len(self.send)>8: print "DatabaseHandler.process> queue", len(self.send)
        if self.state==DatabaseHandler.IDLE: ## handler idle so start work immediately
            ## duplicate code from state machine
            self.work=work
            work.request.execute()
            self.state=DatabaseHandler.EXECUTE
        else:
            self.send.append(work)

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
        if self.state==DatabaseHandler.WAIT:
            ## duplicate code in put()
            self.work=self.send.pop()
            self.work.request.execute()
            self.state=DatabaseHandler.EXECUTE
        if self.state==DatabaseHandler.EXECUTE:
            self.work.response=self.work.request.fetch()
            self.state=DatabaseHandler.FETCH
        elif self.state==DatabaseHandler.FETCH:
            self.work.request.close()
            self.work.request=None
            self.state=DatabaseHandler.CLOSE
        elif self.state==DatabaseHandler.CLOSE:
            self.recv.append(self.work) ## Data now available.
            self.work=None ## Idle
            self.state=DatabaseHandler.IDLE
            if self.send: ## more data to process
                self.state=DatabaseHandler.WAIT
        
    ## Socket must be in "ready" state before processing (idle)
    def read(self):
        pass
    def write(self):
        pass
        
    def get(self):
        if len(self.recv)>1: print "DatabaseHandler.get> queue", len(self.send)
        if self.recv:
            work=self.recv.pop()
            if debug: print "DatabaseHandler.get>", len(self.recv), work.tid, work.response
            return work 
        return None
    
    def shutdown(self):
        self.conn.close()

## Database Tasks

class GetDevices(Task):
    devices=None
    def run(self):
        query=Query("SELECT deviceID,IP,port,device FROM Devices WHERE last IS NULL")
        response=yield query
        self.devices=[]
        for deviceID,IP,port,device in response:
            device=object.Device(IP,port,device,deviceID)
            self.devices.append(device)
        if debug: print "postgres.GetDevices>", self.devices
        for d in self.devices:
            query=Query("SELECT objectID,instance,type,name FROM Objects WHERE deviceID=%s" % (d.id))
            response=yield query
            for o in response:
                d.objects.append(object.Object(*o))
            

## Insert Queries (basic)

class Log(Query):
    def __init__(self,IP,port,instance,value,status=None,objectID=None):
        query="INSERT INTO Log (time,IP,port,instance,value,status,objectID) VALUES (%s,%s,%s,%s,%s,%s,%s);"
        now=psycopg2.TimestampFromTicks(time.time())
        Query.__init__(self,query, now,IP,port,instance,value,status,objectID)

class Object(Query):
    def __init__(self,deviceID,pointID,instance,type,name,description=None):
        query="INSERT INTO Objects (first,deviceID,pointID,instance,type,name,description) VALUES (%s,%s,%s,%s,%s,%s,%s)  RETURNING objectID;"
        now=psycopg2.TimestampFromTicks(time.time())
        Query.__init__(self,query, now,deviceID,pointID,instance,type,name,description)

class Device(Query):
    def __init__(self,IP,port,device,name):
        query="""
UPDATE Devices SET last=%s WHERE IP=%s AND port=%s AND device=%s;
INSERT INTO Devices (first,IP,port,device,name) VALUES (%s,%s,%s,%s,%s)
  RETURNING deviceID;
        """
        now=psycopg2.TimestampFromTicks(time.time())
        Query.__init__(self,query, 
                       now,IP,port,device,
                       now,IP,port,device,name)


## Synchronous Interface

class Database:
    def __init__(self,database='baclog'):
        self.conn=psycopg2.connect(database=database)
        self.database=database

    def query(self,query):
        '''
        Run an asynchronous query synchronously.
        '''
        query.execute()
        result=query.fetch()
        query.close()
        return result
    
    def close(self):
        self.conn.close()
        self.conn=None
        self.database=None
