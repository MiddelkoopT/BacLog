## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream object

import string
trace=False


class Object:
    ## Meta information
    name=None
    description=None
    tags=None
    
    def __init__(self,_device,_type,_instance):
        self.device=_device
        self.type=_type
        self.instance=_instance
        self._hash=hash((_device,_type,_instance))
        
    def __setattr__(self,name,value):
        if name in ('device','type','instance','_hash') and getattr(self,name,None) is not None:
            raise False ## Read only access to definition
        self.__dict__[name]=value
        
    def __repr__(self):
        output=["<%s,%s,%s" % (self.device,self.type,self.instance)]

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
        return self.device==other.device and self.type==other.type and self.instance==other.instance

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


class Value:
    def __init__(self,var,value,time):
        self.var=var
        self.value=value
        self.time=time
        
    def __repr__(self):
        return "%s(%s)" % (self.var, self.value)


class Objects:
    def __init__(self,objects=None):
        if objects is None:
            objects=set()
        assert type(objects)==type(set())
        self.objects=objects
            
    def __iter__(self):
        return self.objects.__iter__()

    def __getitem__(self,index):
        return self.objects[index]
    
    def __contains__(self,object):
        return self.object.has_key(object)
    
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
    
    def add(self,object):
        if isinstance(object, Objects):
            for o in object:
                self.objects.add(o)
        else:
            self.objects.add(object)
            
    def single(self):
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
        result=Objects()
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
        result=Objects(self.objects)
        for tag,value in tags.iteritems():
            result=result.getTag(tag,value)
        return result

    def getTagNot(self,tag):
        result=Objects()
        for o in self.objects:
            if not o.hasTag(tag):
                result.add(o)
        return result

    def getTagsNot(self,tags):
        result=Objects()
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
    def __init__(self):
        self.output=[]
        self.input=[]
        self._send=None
        self._recv=None
        
    def addOut(self,output):
        self.output.append(output)
    
    def connect(self):
        self._send={}
        for stream in self.output:
            for o in stream._input.objects:
                self._send.setdefault(o,[]).append(stream)
    
    def __repr__(self):
        output=['Connection']
        output.append('input:')
        for o in self.input:
            output.append(o._name)
        output.append('output:')
        for o in self.output:
            output.append(o._name)
        print self.output
        return string.join(output)
    
    def send(self,value):
        for stream in self._send.get(value.var,[]):
            stream._recv(value) ## send value to the recv methods of all the streams 

    
class Stream:
    
    def __init__(self,name,*args,**kwargs):
        self._name=name
        self._input=Objects()
        self._output=Objects()
        self._connections=[]
        self._names=[]
        self._var={}
        self._prev=None
        self._run=False
        
        self._plotdata={} ## name:(color,plotdata)
        self._plotname=[] ## plot order
        self._plottime=[]

        self._init(*args,**kwargs)
        
    def __repr__(self):
        output=[self._name]
        output.append('input:')
        for o in self._input:
            name=self._var[o]
            output.append("%s(%s)" % (name,getattr(self,name)))
        return string.join(output)
    
    def _recv(self,value):
        #print "Stream.recv>", self._name, value

        ## In startup mode     
        if not self._run:
            starting=False
            if self._prev is None:
                self._prev=value.time
            for name in self._var.values():
                if getattr(self,name,None) is None:
                    starting=True
                name=self._var[value.var] ## same "Set Variable" below
                setattr(self,name,value.value)
            if starting:
                return
            print "Stream.recv>Started:", self
            self._start() ## compute initial values.
            self._run=True

        ## Set Variable
        name=self._var[value.var]
        setattr(self,name,value.value)
        
        delta=value.time-self._prev
        self._prev=value.time
        deltasec=delta.days*(1440) + delta.seconds+delta.microseconds/1000000.0

        self._compute(deltasec)
        self._plot(value.time)

    def _plot(self,time):
        self._plottime.append(time)
        for name,(color,data) in self._plotdata.iteritems():
            value=getattr(self,name)
            data.append(value)
        
    def _addPlot(self,name,color):
        self._plotname.append(name)
        self._plotdata[name]=(color,[])
        
    def _addIn(self,var,name):
        if isinstance(var,Objects):
            var=var.single()
        self._names.append(name)
        self._var[var]=name
        self._input.add(var)
        setattr(self,name,None)
        
    def _values(self):
        result=[]
        for n in self._names:
            result.append(getattr(self,n))
        return result
            
        
        
class RoomEnthalpy(Stream):
    
    def _init(self,vav):
        self._addIn(vav.getTag('descriptor','AUX TEMP'),'sa')
        self._addIn(vav.getTag('descriptor','FLOW'),'f')
        self._addIn(vav.getTag('descriptor','CTL FLOW MAX'),'mf')
        self._addIn(vav.getTag('descriptor','CTL TEMP'),'t')

        self._addPlot('hin',  (0.121569, 0.313725, 0.552941, 1.0))
        self._addPlot('hout', (1.000000, 0.500000, 0.000000, 1.0))
        self._addPlot('q',    (0.725490, 0.329412, 0.615686, 1.0))
        self._addPlot('hroom',(0.000000, 0.500000, 0.000000, 1.0))
        self._addPlot('error',(1.000000, 0.000000, 0.000000, 1.0))

    def _start(self):
        W=0.008 ## assume humidity ratio of 50% @ 71F
        self.hroom=0.240*self.t+W*(1061+0.444*self.t)
        self.hroom=0 ## FIXME: proper heat loss model needed
        
    def _compute(self,delta):
        #print "RoomEnthalpy.compute>"

        W=0.008 ## assume humidity ratio of 50% @ 71F
        sa,f,mf,t=self._values() ## ordered
        
        ## Sensible q estimate 
        cfm=mf*(f/100.0)
        self.q=cfm*1.08*(sa-t)

        ## Mixed air model.  Assume no change in W
        self.hin =0.240*sa+W*(1061+0.444*sa)
        self.hout=0.240*t +W*(1061+0.444*t)
        
        ## mass ratio of exchanged air, use CF/CFM not mass (small temp range)
        mr=(cfm*delta/60.0)/(181*12)  
        self.hroom=mr*(self.hin-self.hout)+(1.0-mr)*self.hroom
        
        self.error=self.hin-self.hout

        
