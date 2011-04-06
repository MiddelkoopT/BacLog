## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Main I/O and Task scheduler

import select
import time

debug=False
trace=False

class Scheduler:
    def __init__(self):
        if debug: print "Scheduler>"
        self.task={}
        self.work=[]
        self.done=[]
        
        self.cmd=[]
        self.handler=[]
        self.socket={}
    
    def addHandler(self,handler):
        self.handler.append(handler)
        self.socket[handler.socket]=handler
            
    def add(self,task):
        assert isinstance(task, Task)
        self.task[task.tid]=task
        self.done.append(Work(task.tid)) ## Prime
        return task.tid
    
    def put(self,cmd):
        assert isinstance(cmd, Work)
        self.cmd.append(cmd)
    
    def run(self):
        if debug: print "Scheduler.run> start"
        while self.task:
            block=2 ## start off with blocking.
            if self.done: 
                block=0
            while True:
                
                ## fd queue
                r,w,x=[],[],[]
                for h in self.handler:
                    h.reading() and r.append(h.socket)
                    h.writing() and w.append(h.socket)
                    x.append(h.socket)
                if trace: print "Scheduler.run> select",r,w,x,block
                (sr,sw,sx) = select.select(r,w,x,block)
                assert not sx
                if trace: print "Scheduler.run> select", sr,sw,sx
                
                ## Sockets are in "ready" state and will "process"
                ready=[]
                for h in self.handler:
                    h.ready() and ready.append(h)
                
                ## Command queue
                next,cmd=[],[]
                for c in self.cmd:
                    if c.request.done():
                        cmd.append(c)
                    else:
                        next.append(c)
                self.cmd=next

                ## scheduler is empty.
                if (not sr) and (not sw) and (not sx) and (not cmd) and (not ready):
                    if trace: print "Scheduler.run> empty"
                    break
                
                ## Process Data

                block=0 ## Data exists do not block

                ## Recv
                for s in sr:
                    if trace: print "Scheduler.run> read"
                    handler=self.socket[s]
                    handler.read()

                ## Send
                for s in sw:
                    if trace: print "Scheduler.run> write"
                    handler=self.socket[s]
                    handler.write()
                    
                ## Ready
                for h in ready:
                    if trace: print "Scheduler.run> process"
                    h.process() 
    
                ## Cmd (not a fd handler)
                for c in cmd:
                    if trace: print "Scheduler.run> cmd"
                    c.response=c.request.get()
                    self.done.append(c)
            
            ## Pair responses
            for h in self.handler:
                while h.recv:
                    work=h.get()  ## Handlers do the paring.
                    if work:
                        self.done.append(work)
                    if trace: print "Scheduler.run> pair", work
            
            ## Deliver responses to tasks and collect new messages.
            while self.done:
                try:
                    work=self.done.pop(0)
                    if debug: print "Scheduler.run> done", work
                    task=self.task[work.tid]
                    send=task.send(work.response) ## coroutine yield
                    if send:
                        if debug: print "Scheduler.run> work", send
                        send._handler.put(Work(work.tid,send))
                except StopIteration:
                    if debug: print "Scheduler.run> %d exited" % work.tid
                    del self.task[work.tid]
                    continue

        if debug: print "Scheduler.run> done", self.work, self.done
        assert not self.work and not self.done
        
    def shutdown(self):
        for h in self.handler:
            h.shutdown()

class Task:
    tid=0
    scheduler=Scheduler() ## Global default scheduler
    def __init__(self):
        Task.tid+=1
        self.tid=Task.tid
        self.send=self.run().send ## create coroutine link send() 

    def run(self):
        assert False ## Run not implemented in subclass
        
    def send(self):
        assert False ## send should point to coroutine send()

class Work:
    """
    Schedule work
    All Scheduler work uses this class 
    """
    def __init__(self,tid,request=None):
        self.tid=tid
        self.request=request
        self.response=None
    
    def __repr__(self):
        return "work:%d" % self.tid

## Internal scheduler commands.

class Wait:
    '''
    Wait(sleep time) command
    '''
    _handler=Task.scheduler
    def __init__(self,sleep):
        self.sleep=sleep
        self.start=time.time()
        
    def done(self):
        if time.time() > self.start+self.sleep:
            if debug: print "Wait.done>", self.start
            return True
        return False
    
    def get(self):
        return True

## Initialize scheduler.

def init():
    return Task.scheduler
