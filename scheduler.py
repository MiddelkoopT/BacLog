#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0
## Main I/O and Task scheduler

import select

debug=False
trace=False

class Task:
    tid=0
    scheduler=None
    def __init__(self):
        Task.tid+=1
        self.tid=Task.tid
        self.send=self.run().send

class Work:
    def __init__(self,tid,request=None):
        self.tid=tid
        self.request=request
        self.response=None
    
    def __str__(self):
        return "work:%d" % self.tid

class Scheduler:
    def __init__(self):
        if debug: print "Scheduler>"
        self.task={}
        self.work=[]
        self.done=[]
        
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
        
    def run(self):
        if debug: print "Scheduler.run> start"
        while self.task:
            block=5 ## start off with blocking.
            if self.done: 
                block=0
            while True:
                if debug: print "Scheduler.run> select",block
                r,w,x=[],[],[]
                for h in self.handler:
                    r.append(h.socket)
                    h.send and w.append(h.socket)
                    x.append(h.socket)
                (sr,sw,sx) = select.select(r,w,x,block)
                assert not sx

                ## Nothing to do.
                if (not sr) and (not sw) and (not sx):
                    if debug: print "Scheduler.run> empty"
                    break

                block=0 ## Data exists do not block

                ## Send
                for s in sw:
                    if trace: print "Scheduler.run> write"
                    handler=self.socket[s]
                    handler.write()
    
                ## Recv
                for s in sr:
                    if trace: print "Scheduler.run> read"
                    handler=self.socket[s]
                    handler.read()
            
            ## Pair responses
            for h in self.handler:
                while h.recv:
                    work=h.get()  ## Handlers do the paring.
                    if work:
                        self.done.append(work)
                    if debug: print "Scheduler.run> pair", work
            
            ## Deliver responses to tasks and collect new messages.
            while self.done:
                try:
                    work=self.done.pop(0)
                    task=self.task[work.tid]
                    if debug: "Scheduler.run> done", work.tid, work.response
                    send=task.send(work.response) ## Main coroutine entry point
                    if send:
                        if debug: print "Scheduler.run> work", send
                        send._handler.put(Work(work.tid,send))
                except StopIteration:
                    if debug: print "Scheduler.run> %d exited" % work.tid
                    del self.task[work.tid]
                    continue

        print "Scheduler.run> done", self.work, self.done
        assert not self.work and not self.done
        
    def shutdown(self):
        for h in self.handler:
            h.shutdown()