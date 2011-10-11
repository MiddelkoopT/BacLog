## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Graphics

from time import mktime

from traits.api import HasTraits
from chaco.api import HPlotContainer, OverlayPlotContainer, PlotAxis #, PlotGrid
from traitsui.api import View, Item
from enable.component_editor import ComponentEditor
from chaco.api import create_line_plot
from chaco.tools.api import BroadcasterTool, PanTool, DragZoom

class Graph(HasTraits):
    plot=None
    traits_view=View(Item('plot',editor=ComponentEditor(), show_label=False),
                     width=1200, height=1024, resizable=True, title="Plot")
    
    def __init__(self):
        super(Graph,self).__init__()

        self.plot_area = OverlayPlotContainer(border_visible=True)
        self.container = HPlotContainer(padding=50, bgcolor="transparent")

    def add(self,series,dash="solid"):
        ptime=series._plottime
        plots=series._plotdata
        names=series._plotname

        ## hour bar (start of the hour).
        hour,seconds=[],[]
        for t in ptime:
            hour.append(showtime(t))
            seconds.append(mktime(t.timetuple())+t.microsecond/1000000.0)
            
        plot=create_line_plot((seconds,hour),color=(0.500000, 0.500000, 0.500000, 0.5))
        self.plot_area.add(plot)

        ## Attach broadcaster to special grid
        broadcaster = BroadcasterTool()
        plot.tools.append(broadcaster)

        for name in names:
            color,data=plots[name]
            plot=create_line_plot((seconds,data),color=color,dash=dash)
            self.plot_area.add(plot)
    
            axis = PlotAxis(orientation="left", resizable="v",
                            mapper = plot.y_mapper,
                            axis_line_color=color,
                            tick_color=color,
                            tick_label_color=color,
                            title_color=color,
                            bgcolor="transparent",
                            title = name,
                            border_visible = True,)
            axis.bounds = [60,0]
            axis.padding_left = 1
            axis.padding_right = 1
            self.container.add(axis)


        ## Tools
        for plot in self.plot_area.components:
            broadcaster.tools.append(PanTool(plot))
            broadcaster.tools.append(DragZoom(plot,maintain_aspect_ratio=False,drag_button='right',restrict_domain=True))
        
    def run(self):

        ## Time axis (first one)
        plot=self.plot_area.components[0]
        time = PlotAxis(orientation="bottom", component=plot, mapper=plot.x_mapper)
        plot.overlays.append(time)
        #grid = PlotGrid(mapper=plot.x_mapper, orientation="vertical",
        #                line_color="lightgray", line_style="dot")
        #plot.underlays.append(grid)

        ## Plot
        self.container.add(self.plot_area)
        self.plot=self.container

        self.configure_traits()

######
## Util

def showtime(time):
    if time.hour>12:
        return (24-time.hour)-12
    else:
        return time.hour-12
