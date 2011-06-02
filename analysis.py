#!/usr/bin/python
## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Stream compute test code.

import psycopg2
import re
import string
from time import mktime

class Object:
    def __init__(self,_device,_type,_instance):
        self.device=_device
        self.type=_type
        self.instance=_instance
        self.tags={}
        ## Backnet information
        self.name=None
        self.description=None
        ## State
        self.value=None
        self.time=None

    def __repr__(self):
        output=["<%s,%s,%s>" % (self.device,self.type,self.instance)]
        if self.value is not None:
            output.append('(')
            output.append(str(self.value))
            output.append(')')

        if self.name is not None:
            output.append("[%s" % (self.name))
            if self.description:
                output.append(';'+self.description)
            output.append(']')

        if self.tags:
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
    
    def eq(self,device,type,instance):
        return self.device==device and self.type==type and self.instance==instance

    def addTag(self,name,value=True):
        self.tags[name]=value
        
    def hasTag(self,tag):
        return self.tags.has_key(tag)
    
    def getTag(self,tag):
        return self.tags[tag]
    
    def getTags(self):
        return self.tags.keys()
    
    def tag(self):
        ## auto tagging heuristics
        
        ## Building
        for r in re.finditer('^B(\d+)[\._:]', self.name):
            self.addTag('building',int(r.group(1)))

        ## Room/AHU and other numbered units
        for r in re.finditer('[\._](ROOM|AHU|VAV|VFD)(\d+)', self.name):
            tag=string.lower(r.group(1))
            self.addTag(tag,int(r.group(2)))
        
        ## Find closets
        for r in re.finditer('[\._](C\d+[A-Z])[\._]', self.name):
            self.addTag('closet',r.group(1))

        ## Find Telcom
        for r in re.finditer('[\._]ROOM(TR[A-Z\d]+)[\._]', self.name):
            self.addTag('closet',r.group(1))
            self.addTag('telcon')
            
        ## Find Other
        for r in re.finditer('[\._](PMPM)ROOM[\._]', self.name):
            self.addTag('closet',string.upper(r.group(1)))
            
        ## Find pump VFD's
        for r in re.finditer('[\._]PMP[\._](\d+)[\._]VFD', self.name):
            self.addTag('pump',r.group(1))
            self.addTag('vfd')
            
        ## Find any pump
        for r in re.finditer('[\._](CHW|HHW)?PMP(\d+)[\._:-]', self.name):
            self.addTag('pump',int(r.group(2)))
            self.addTag(string.upper(r.group(1)))
            
        ## Add material tag
        map={'STEAM':'steam', 'STM':'steam', 'CHW':'chw', 'HHW':'hhw'}
        for r in re.finditer("[\._](%s)" % string.join(map.keys(),'|'), self.name):
            self.addTag(map[r.group(1)])
            
        ## derive unit and descriptor/address from name
        for r in re.finditer('^B\d+[\._]([A-Z\d_\.]+)([:-]([A-Z\d \.-]+))?$', self.name):
            self.addTag('unit',r.group(1))
            if r.group(2):
                self.addTag('descriptor',r.group(3))
            
        ## Tag keywords after : or -
        map={'APPLICATION':'application'}
        for r in re.finditer('[:-](APPLICATION)$', self.name):
            if self.instance % 100 == 2:
                self.addTag(map[r.group(1)])
                
        ## FLN devices are spaced by 100 > 10000
        if self.instance >= 10000:
            self.addTag('module',self.instance/100)
            self.addTag('address',self.instance%100)
            
            
class Objects:
    def __init__(self,objects=None):
        if objects is None:
            objects=[]
        self.objects=objects    
            
    def __iter__(self):
        return self.objects.__iter__()

    def __getitem__(self,index):
        return self.objects[index]
    
    def __contains__(self,object):
        for o in self.objects:
            if o.device==object.device and o.type==object.type and o.instance==object.instance:
                return True
        return False

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
                self.objects.append(o)
        else:
            self.objects.append(object)
            
    def updateValue(self,object,value=None,time=None):
        '''
        Updates the 'value' of the corrisponding object and returns the previous value
        '''
        for o in self.objects:
            if o.device==object.device and o.type==object.type and o.instance==object.instance:
                previous,last=o.value,o.time
                o.value=value
                o.time=time
        return previous,last

    def tag(self):
        for o in self.objects:
            o.tag()
        ## System wide
        #self.tagUnits()
        
    def get(self,device,type,instance):
        for o in self.objects:
            if o.device==device and o.type==type and o.instance==instance:
                return o
    
    def getTag(self,tag,value=None):
        result=[]
        if value is None:
            for o in self.objects:
                if o.hasTag(tag):
                    result.append(o)
        else:
            for o in self.objects:
                if o.hasTag(tag) and value==o.getTag(tag):
                    result.append(o)
        return Objects(result)

    def getTagNot(self,tag):
        result=[]
        for o in self.objects:
            if not o.hasTag(tag):
                result.append(o)
        return Objects(result)

    def getTagsNot(self,tags):
        result=[]
        for o in self.objects:
            found=False
            for t in tags:
                if t in o.getTags():
                    found=True
            if not found:
                result.append(o)
        return Objects(result)
    
    def values(self):
        values=[]
        for o in self.objects:
            values.append(o.value)
        return values

    
class Analysis:
    database='mtim'

    def __init__(self):
        print "analysis.py"
        self.db=psycopg2.connect(database=self.database)
        self.objects=None
        
    def getDevices(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,name FROM Devices")
        devices=cur.fetchall()
        cur.close()
        return devices
    
    def getObjects(self):
        cur=self.db.cursor()
        cur.execute("SELECT device,type,instance ,Objects.name,Objects.description FROM Devices JOIN Objects USING (deviceID)")
        objects=[]
        for r in cur:
            device,type,instance,name,description=r
            o=Object(device,type,instance)
            o.name=name
            if description != None or description != '':
                o.description=description
            objects.append(o)
        return Objects(objects)

    def check(self):
        ## QC check 
        objects=self.objects              
        print "!building", objects.getTagNot('building')
        print '!room vav',objects.getTagsNot(['room','closet']).getTag('vav')
        print "!unit", objects.getTagNot('unit')
        
        print "untaged", objects.getTagsNot(['room','closet','ahu','pump'])
        print '!descriptor',objects.getTagNot('descriptor')

    def run(self):
        print self.getDevices()
        objects=self.objects=self.getObjects()
        objects.tag()
        
        ## Gather target objects
        room=objects.getTag('room',241)
        stream=Objects()
        for a in [15,75,77,78]: ## SA,Flow,Max,T
            stream.add(room.getTag('address',a))
        #stream.add(objects.get(9040,0,5))  ## RAH
        #stream.add(objects.get(9040,0,6))  ## SAT
        #stream.add(objects.get(9040,0,15)) ## RAH2
        print 'stream',stream
        
        cur=self.db.cursor()
        cur.execute("SELECT time,device,type,instance,value FROM Data2 ORDER BY Time")
        print cur.rowcount
        
        ## Preload.
        for time,device,type,instance,value in cur:
            o=Object(device,type,instance)
            if o not in stream:
                continue
            stream.updateValue(o,value,time)
            done=True
            for o in stream:
                if o.value is None:
                    done=False
                    break
            if done:
                break
        #print "preload",stream
        
        ## Analysis loop.
        data={}
        ptime=data['time']=[]
        pq=data['q']=[]
        pt=data['t']=[]
        pmcp=data['mcp']=[]
        
        iqt=0.0
        for time,device,type,instance,value in cur:
            o=Object(device,type,instance)
            if o in stream:
                previous,last=stream.updateValue(o,value,time)
                ptime.append(mktime(time.timetuple())+time.microsecond/1000000.0)
                sa,f,mf,t=stream.values()
                q=mf*(f/100.0)*1.08*(sa-t)

                # integrate qt
                td=(time-last)
                tdh=td.microseconds/1000000.0+td.seconds+td.days*(1440.0)
                iqt+=q*tdh

                if o.eq(9040,1,12478):
                    mcp=iqt*(t-previous)
                    iqt=0.0
                
                pmcp.append(mcp)
                pq.append(q)
                pt.append(t)

        print len(data['time'])

        cur.close()
        Graph(data,['q','t','mcp']).run()

######
## Graph

COLORS = [
        (0.725490, 0.329412, 0.615686, 1.0),
        (0.121569, 0.313725, 0.552941, 1.0),
        (1.000000, 0.000000, 0.000000, 1.0)
        ]

from enthought.traits.api import HasTraits
from enthought.chaco.api import Plot, ArrayPlotData, HPlotContainer, OverlayPlotContainer, PlotAxis, PlotGrid
from enthought.traits.ui.api import View, Item
from enthought.enable.component_editor import ComponentEditor
from enthought.chaco.api import create_line_plot
from enthought.chaco.tools.api import BroadcasterTool, PanTool, DragZoom

import numpy as np


class Graph(HasTraits):
    plot=None
    traits_view=View(Item('plot',editor=ComponentEditor(), show_label=False),
                     width=1024, height=1024, resizable=True, title="Plot")
    
    def __init__(self,data,series):
        super(Graph,self).__init__()
        
        plot_area = OverlayPlotContainer(border_visible=True)
        container = HPlotContainer(padding=50, bgcolor="transparent")

        colors=COLORS
        for y in series:
            color = colors.pop(0)
            plot=create_line_plot((data['time'],data[y]),color=color)
            plot_area.add(plot)
    
            axis = PlotAxis(orientation="left", resizable="v",
                            mapper = plot.y_mapper,
                            axis_line_color=color,
                            tick_color=color,
                            tick_label_color=color,
                            title_color=color,
                            bgcolor="transparent",
                            title = y,
                            border_visible = True,)
            axis.bounds = [60,0]
            axis.padding_left = 5
            axis.padding_right = 5
            container.add(axis)

        # time (last plot)
        time = PlotAxis(orientation="bottom", component=plot, mapper=plot.x_mapper)
        plot.overlays.append(time)
        grid = PlotGrid(mapper=plot.x_mapper, orientation="vertical",
                        line_color="lightgray", line_style="dot")
        plot.underlays.append(grid)

        ## Tools
        broadcaster = BroadcasterTool()
        for plot in plot_area.components:
            broadcaster.tools.append(PanTool(plot))
            broadcaster.tools.append(DragZoom(plot,maintain_aspect_ratio=False,drag_button='right'))
        plot.tools.append(broadcaster)

        ## Plot
        container.add(plot_area)
        self.plot=container
        
    def run(self):
        self.configure_traits()

######
## Main

if __name__=='__main__':
    Analysis().run()
    