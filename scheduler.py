#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

## Main i/o scheduler

class Task:
    tid=0
    def __init__(self):
        Task.tid+=1
        self.tid=Task.tid
        self.target=self.run("Start")
        
    def start(self):
        result=self.target.next()
        print "Task.start>", result
        
    def run(self,msg):
        print 'Task.run> A', self.tid
        yield True
        result = yield 10
        print 'Task.run> B', self.tid, result
        result = yield 20
        print 'Task.run> C', self.tid, result
        return


class Scheduler:
    def __init__(self):
        self.task={}
        self.queue=[]
    def add(self,task):
        assert isinstance(task, Task)
        self.task[task.tid]=task
        self.queue.append(task)
        task.start()
    
    def run(self):
        print "Scheduler.run>"
        tick=100
        while self.queue:
            tick+=1
            task=self.queue.pop(0)
            try:
                msg=task.target.send(tick)
            except StopIteration:
                print "Scheduler.run> %d exited" % task.tid
                continue
            print "Scheduler.run>", tick, task.tid, msg
            self.queue.append(task)



if __name__=='__main__':
    s=Scheduler()
    t1=Task()
    t2=Task()
    
    s.add(t1)
    s.add(t2)
    
    s.run()