## BacLog Copyright 2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Graphics

from time import mktime

from enthought.traits.api import HasTraits
from enthought.chaco.api import Plot, ArrayPlotData, HPlotContainer, OverlayPlotContainer, PlotAxis, PlotGrid
from enthought.traits.ui.api import View, Item
from enthought.enable.component_editor import ComponentEditor
from enthought.chaco.api import create_line_plot
from enthought.chaco.tools.api import BroadcasterTool, PanTool, DragZoom

class Graph(HasTraits):
    plot=None
    traits_view=View(Item('plot',editor=ComponentEditor(), show_label=False),
                     width=1200, height=1024, resizable=True, title="Plot")
    
    def __init__(self,ptime,plots,names):
        super(Graph,self).__init__()
        
        plot_area = OverlayPlotContainer(border_visible=True)
        container = HPlotContainer(padding=50, bgcolor="transparent")

        ## hour bar (start of the hour).
        hour,seconds=[],[]
        for t in ptime:
            hour.append(showtime(t))
            seconds.append(mktime(t.timetuple())+t.microsecond/1000000.0)
            
        plot=create_line_plot((seconds,hour),color=(0.500000, 0.500000, 0.500000, 0.5))
        plot_area.add(plot)

        ## Attach broadcaster to special grid
        broadcaster = BroadcasterTool()
        plot.tools.append(broadcaster)

        for name in names:
            color,data=plots[name]
            plot=create_line_plot((seconds,data),color=color)
            plot_area.add(plot)
    
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
            container.add(axis)

        # time (last plot)
        time = PlotAxis(orientation="bottom", component=plot, mapper=plot.x_mapper)
        plot.overlays.append(time)
        #grid = PlotGrid(mapper=plot.x_mapper, orientation="vertical",
        #                line_color="lightgray", line_style="dot")
        #plot.underlays.append(grid)

        ## Tools
        for plot in plot_area.components:
            broadcaster.tools.append(PanTool(plot))
            broadcaster.tools.append(DragZoom(plot,maintain_aspect_ratio=False,drag_button='right'))

        ## Plot
        container.add(plot_area)
        self.plot=container
        
    def run(self):
        self.configure_traits()

######
## Util

def showtime(time):
    if time.hour>12:
        return (24-time.hour)-12
    else:
        return time.hour-12
