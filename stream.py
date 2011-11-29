## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream object

import string
trace=False


class Instance:
    ## Meta information
    name=None
    description=None
    tags=None
    
    def __init__(self,_device,_type,_instance):
        self.device=_device
        self.otype=_type
        self.oinstance=_instance
        self._hash=hash((_device,_type,_instance))
        
    def __setattr__(self,name,value):
        if name in ('device','otype','oinstance','_hash') and getattr(self,name,None) is not None:
            raise Exception('attempt to change read only definition')
        self.__dict__[name]=value
        
    def __repr__(self):
        output=["<%s,%s,%s" % (self.device,self.otype,self.oinstance)]

        if self.name is not None:
            output.append("|%s:%s" % (self.tags.get('unit'),self.tags.get('descriptor')))
            if trace and self.description:
                output.append(';'+self.description)
        output.append('>')

        if trace and self.tags:
            tags=[]
            output.append('{')
            for t,v in self.tags.items():
                if v is True:
                    tags.append(t)
                else:
                    tags.append('%s:%s' % (t,v))
            output.append(string.join(tags,', '))
            output.append('}')
        
        return string.join(output,'')
    
    def __hash__(self):
        return self._hash
    
    def __eq__(self,other):
        return self.device==other.device and self.otype==other.otype and self.oinstance==other.oinstance

    def setTag(self,name,value=True):
        if self.tags is None: self.tags={} 
        self.tags[name]=value
        
    def hasTag(self,tag):
        return self.tags.has_key(tag)
    
    def getTag(self,tag):
        '''
        Get tag value, False indicates tag does not exist
        '''
        return self.tags.get(tag,False)
    
    def getTags(self):
        return self.tags.keys()
    

class Variable:
    
    def __init__(self,name,source=None):
        self.name=name
        self.source=source
        if source:
            self._hash=hash((source.device,source.otype,source.oinstance,name))
        else:
            self._hash=hash(name)

    def __setattr__(self,name,value):
        if name in ('device','otype','oinstance','_hash') and getattr(self,name,None) is not None:
            raise Exception('attempt to change read only definition')
        self.__dict__[name]=value
        
    def __hash__(self):
        return self._hash
    
    def __eq__(self,other):
        return self.name==other.name and self.source==other.source
    
    def __repr__(self):
        return "%s:%s" % (self.source,self.name)
    
    ## chain queries to source
    def getTag(self,tag):
        return self.source.getTag(tag)
        

class Value:
    def __init__(self,var,value,time,wave):
        self.var=var
        self.value=value
        self.time=time
        self.wave=wave
        
    def __repr__(self):
        return "%s(%s)+%d" % (self.var, self.value, self.wave)


class InstanceList:
    def __init__(self,objects=None):
        if objects is None:
            objects=set()
        assert type(objects)==type(set())
        self.objects=objects
            
    def __iter__(self):
        return self.objects.__iter__()

    def __getitem__(self,index):
        return self.objects[index]
    
    def __contains__(self,obj):
        return obj in self.objects
    
    def __len__(self):
        return self.objects.__len__()

    def __repr__(self):
        if not self.objects:
            return '[]'
        output=['[']
        for o in self.objects:
            output.append(str(o))
        output.append(']')
        return string.join(output,"\n  ")
    
    def add(self,instance):
        if isinstance(instance, InstanceList):
            for o in instance:
                self.objects.add(o)
        else:
            self.objects.add(instance)
            
    def single(self):
        '''
        Convert into a single Instance
        '''
        assert len(self.objects)==1
        return self.objects.pop()
            
    def setTag(self,tag,value=True):
        for o in self.objects:
            if o.hasTag(tag):
                o.setTag(tag,value)
        return self
                
    def getTag(self,tag,value=True):
        '''
        True value matches any tag value.
        False matches the absence of a tag.
        '''
        result=InstanceList()
        if value is True:
            for o in self.objects:
                if o.hasTag(tag):
                    result.add(o)
        elif value is False:
            for o in self.objects:
                if not o.hasTag(tag):
                    result.add(o)
        else:
            for o in self.objects:
                if o.hasTag(tag) and value==o.getTag(tag):
                    result.add(o)
        return result

    def getTags(self,tags):
        '''
        Get objects that match all the conditions (AND)
        True indicates a wildcard
        False indicates absence of a tag.
        '''
        result=InstanceList(self.objects)
        for tag,value in tags.iteritems():
            result=result.getTag(tag,value)
        return result

    def getTagNot(self,tag):
        result=InstanceList()
        for o in self.objects:
            if not o.hasTag(tag):
                result.add(o)
        return result

    def getTagsNot(self,tags):
        result=InstanceList()
        for o in self.objects:
            found=False
            for t in tags:
                if t in o.getTags():
                    found=True
            if not found:
                result.add(o)
        return result

    def getValues(self,tag):
        '''
        Get unique values given a tag name
        '''
        result={False:False}
        for o in self.objects:
            result[o.getTag(tag)]=True
        del result[False]
        return result.keys()


class Connection:
    def __init__(self,name):
        self.name=name
        self.output=[]
        self.input=[]
        self._send={}
        
    def addOut(self,sink):
        assert sink not in self.output ## Adding sink twice
        self.output.append(sink)
        link=[]
        for source in self.input:
            for obj in source._query():
                if sink._register(obj):
                    link.append(obj)
                    source._subscribe(obj)
        for l in link:
            self._send.setdefault(l,[]).append(sink)
            
        #print 'Connection.addOut>', self.name, link, self._send
        

    def addIn(self,source):
        assert source not in self.input ## Adding sink twice
        self.input.append(source)
        source._connections.append(self) ## FIXME: Move to subscribe call
        link=[]
        for sink in self.output:
            for obj in source._query():
                if sink._register(obj):
                    link.append(obj)
                    source._subscribe(obj)
        for l in link:
            self._send.setdefault(l, []).append(sink)
        #print 'Connection.addIn> ', self.name, link, self._send

    def __str__(self):
        return "%s@Connection" % self.name
        
    def __repr__(self):
        output=["%s@Connection[" % self.name]
        for o in self.input:
            output.append(o._name)
        output.append(';')
        for o in self.output:
            output.append(o._name)
        output.append(']')
        return string.join(output)
    
    def send(self,value):
        for stream in self._send.get(value.var,[]):
            stream._recv(value) ## send value to the recv methods of all the streams
        for stream in self._send.get(value.var,[]):
            stream._notify() ## notify connections of changes.  

    
class Stream:

    ## Options
    _plot=None
    
    def __init__(self,name,*args,**kwargs):
        self._name=name             # name of stream.
        self._input=InstanceList()  # list of input objects
        self._output=InstanceList() # list of output objects
        self._connections=[]        # list of connections

        self._names=[]          # ordered list of variable names in class
        self._var={}            # var:name
        self._value={}          # var:value

        self._previousIn={}     # var:previous_value
        self._previousOut={}    # var:previous_value
        self._last=None         # last update for delta
        self._wave=0            # last seen wave number

        self._run=False         # stream running (start complete)
        
        self._plotdata={}       # name:(color,plotdata)
        self._plotname=[]       # plot order
        self._plottime=[]       # time axis

        self._init(*args,**kwargs)
        
    def __str__(self):
        return "%s@Stream" % self._name
    
    def __repr__(self):
        output=["%s@Stream[" % self._name]
        for i in self._input:
            name=self._var.get(i,str(i))
            output.append("%s(%s)" % (name,self._previousIn[i]))
        output.append(';')
        for o in self._output:
            name=self._var.get(o,str(o))
            output.append("%s(%s)" % (name,self._previousOut[o]))
        output.append(']')
        return string.join(output)
    
    def _missing(self):
        result=[]
        for i in self._input:
            if self._previousIn[i] is None:
                result.append(i)
        return result
    
    def _recv(self,value):
        #if self._run:
        #    print "Strem.recv>",self._name, value, self._wave, value.time-self._last

        ## In startup mode (logic closely mirrors run)    
        if not self._run:
            for i in self._input:
                ## Check if incomplete if so set value and return.
                if self._previousIn[i] is None:
                    self._last=value.time
                    self._previousIn[value.var]=value.value
                    self._value[value.var]=value
                    name=self._var.get(value.var,None)
                    if name:
                        setattr(self,name,value.value)
                    return

            print "Stream.recv>Started:", self
            self._start() ## compute initial values.
            self._run=True
            
        ## Consistency check
        if value.time<self._last:
            print self._last, value.time, value  ## asserts on next line
        assert value.time>=self._last                           ## data out of order
        assert value.time>self._last or value.wave>=self._wave  ## data out of order 

        ## Run mode (closely mirrors startup)

        ## Set Variable
        self._value[value.var]=value
        name=self._var.get(value.var,None)
        if name is not None:
            setattr(self,name,value.value)

        ## Calculate time delta and wave
        self._wave=value.wave
        delta=value.time-self._last
        self._last=value.time
        deltasec=delta.days*(1440) + delta.seconds+delta.microseconds/1000000.0

        ## Computation
        self._compute(value,deltasec)
        
        if self._plot:
            self._plotValues(value.time)

        ## Done. update previous input 
        self._previousIn[value.var]=value.value


    def _notify(self):
        ## Send changed values to connections.
        for o in self._output:
            assert self._var[o] is not None ## output not in variable table
            v=getattr(self,self._var[o])
            if v!=self._previousOut.get(o,None):
                self._send(o,v) ## send changed value to connections
                self._previousOut[o]=v
        

    def _send(self,obj,value):
        for c in self._connections:
            c.send(Value(obj,value,self._last,self._wave+1)) ## send value to connections
        
                
    def _addName(self,name,var,value=None):
        if name is None:
            return
        self._names.append(name)
        self._var[var]=name
        setattr(self,name,value)

    def _addIn(self,var,name=None):
        self._addName(name,var)
        self._input.add(var)
        self._previousIn[var]=None
        
    def _addOut(self,var,name=None):
        self._addName(name,var)
        self._output.add(var)
        self._previousOut[var]=None

    def _plotValues(self,time):
        self._plottime.append(time)
        for name,(color,data) in self._plotdata.iteritems(): #@UnusedVariable
            value=getattr(self,name)
            data.append(value)
        
    def _addPlot(self,name,color):
        self._plotname.append(name)
        self._plotdata[name]=(color,[])

    def _values(self):
        '''
        Returns the values in order
        '''
        result=[]
        for n in self._names:
            result.append(getattr(self,n))
        return result

    ## Default subclass methods
    
    def _register(self,var):
        '''
        Return True if interested in receiving this object.
        '''
        return var in self._input
    
    def _query(self):
        '''
        Return the set of available output objects
        '''
        return self._output

    def _subscribe(self,vars): #@ReservedAssignment
        '''
        Notify that an output objects has been subscribed.
        '''
        return True

    def _start(self):
        '''
        Stream is done pre-loading
        '''
        return True

        