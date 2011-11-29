## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Graphics

from time import mktime

from traits.api import HasTraits
from chaco.api import HPlotContainer, OverlayPlotContainer, PlotAxis #, PlotGrid
from traitsui.api import View, Item
from enable.component_editor import ComponentEditor
from chaco.api import create_line_plot
from chaco.tools.api import BroadcasterTool, PanTool, DragZoom
from enable.colors import color_table

class Line():

    def __init__(self,name,color):
        self.name=name
        self.time=[]
        self.data=[]
        self.color=color

    def add(self,value):
        self.time.append(value.time)
        self.data.append(value.value)
        

class Series():
    _color=0 ## auto increment colors
    _colors=color_table.keys()
    
    def __init__(self,name):
        self.name=name
        self.line={}    # set:(x,y)
        
    def addLine(self,name,color=None):
        if color is None:
            self._color+=1
            color=self._colors[self._color]

        self.line[name]=Line(name,color)
        
    def add(self,name,value):
        #if not self.line.has_key(name):
        #    self.addLine(name)
        self.line[name].add(value)


class Graph(HasTraits):
    plot=None
    traits_view=View(Item('plot',editor=ComponentEditor(), show_label=False),
                     width=1200, height=1024, resizable=True, title="BacLog")
    
    def __init__(self):
        super(Graph,self).__init__()
        self.plot_area = OverlayPlotContainer(border_visible=True)
        self.container = HPlotContainer(padding=50, bgcolor="transparent")

    def add(self,series,limit=None):
        
        broadcaster = BroadcasterTool()
        
        for name,line in series._plot.line.items():
            if limit is not None and name not in limit:
                continue
            if line.time==[]:
                print "Graph.add> empty:", name
                continue
            plot=create_line_plot((seconds(line.time),line.data),color=line.color)
            self.plot_area.add(plot)

            axis = PlotAxis(orientation="left", resizable="v",
                            mapper = plot.y_mapper,
                            bgcolor="transparent",
                            title = name,
                            border_visible = True,)
            ## Visual style
            axis.bounds = [60,0]
            axis.padding_left = 1
            axis.padding_right = 1
            self.container.add(axis)

            ## Tools (attach to all for now)
            plot.tools.append(broadcaster)
            broadcaster.tools.append(PanTool(plot))
            broadcaster.tools.append(DragZoom(plot,maintain_aspect_ratio=False,drag_button='right',restrict_domain=True))

        
    def run(self):

        ## Time axis (first one)
        plot=self.plot_area.components[0]
        time = PlotAxis(orientation="bottom", component=plot, mapper=plot.x_mapper)
        plot.overlays.append(time)

        ## Plot
        self.container.add(self.plot_area)
        self.plot=self.container

        self.configure_traits()

######
## Utilities

def seconds(time):
    result=[]
    for t in time:
        result.append(mktime(t.timetuple())+t.microsecond/1000000.0)
    return result

def showtime(time):
    if time.hour>12:
        return (24-time.hour)-12
    else:
        return time.hour-12
