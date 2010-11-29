#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

## Main i/o scheduler

class Task:
    tid=0
    def __init__(self):
        Task.tid+=1
        self.tid=Task.tid
        self.target=self.run()
        self.send=self.target.send
        
    def run(self):
        print 'Task.run> startup'
        result = yield Message("A%d"%self.tid,10)
        print 'Task.run> A', self.tid, result
        result = yield Message("B%d"%self.tid,20)
        print 'Task.run> B', self.tid, result
        return

class MessageHandler:
    def send(self,message):
        print "MessageHandler.send>", message

class Message:
    _handler=MessageHandler()  ## private to scheduler
    def __init__(self,remote,message=None,wait=True):
        self.remote=remote
        self.message=message
        self.wait=wait
    def __str__(self):
        return "[[%s:%s]]" % (self.remote,self.message)
    
class Work:
    def __init__(self,task,send=None):
        self.task=task
        self.send=send
        self.recv=None
        
class Scheduler:
    def __init__(self):
        self.task={}
        self.work=[]
        self.done=[]
    
    def add(self,task):
        assert isinstance(task, Task)
        self.task[task.tid]=task
        self.done.append(Work(task)) ## Prim
    
    def run(self):
        print "Scheduler.run> start"
        tick=100
        while self.work or self.done:
            for work in self.work:
                tick+=1
                #print "Scheduler.run> work", tick, work.task.tid
                ## Send message
                print "Scheduler.run> send", tick, work.task.tid, work.send
                ## Recv message 
                work.recv=work.send
                work.recv.message+=1
                self.done.append(work)
                print "Scheduler.run> recv", tick, work.task.tid, work.send
            ## Reset work queue
            self.work=[] 
                
            ## Deliver responses.
            for work in self.done:
                tick+=1
                print "Scheduler.run> done", tick, work.task.tid, work.recv
                try:
                    send=work.task.send(work.recv)
                    ## Process message.
                except StopIteration:
                    print "Scheduler.run> %d exited" % work.task.tid
                    del self.task[work.task.tid]
                    continue
                ## Append new work.
                self.work.append(Work(work.task,send))
            ## reset done queue
            self.done=[]

        print "Scheduler.run> exit", self.work, self.done
        assert not self.work and not self.done



if __name__=='__main__':
    s=Scheduler()
    t1=Task()
    t2=Task()
    
    s.add(t1)
    s.add(t2)
    
    s.run()