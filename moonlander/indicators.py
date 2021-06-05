import bokeh
import numpy as np
import pandas as pd
from talib.abstract import *
class IndicatorBase:
    def __init__(self, plot = True, plot_separately = False):
        self.plot = plot
        self.plot_separately = plot_separately
        
    def preprocess_dataframe(self, data):
        cols = ['high', 'low', 'open', 'close', 'volume']
        HLOCV = {key: data[key].values for key in data if key in cols}
        return HLOCV

class SimpleMovingAverage(IndicatorBase):
    def __init__(self, period, color = 'orange', plot = True, plot_separately = False):
        super().__init__(plot, plot_separately)
        self.period = period

        # Plotting
        self.color = color
        
    def compute(self, data):
        self.data = data
        data = self.preprocess_dataframe(data)
        self.values = SMA(data, self.period)

        self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(self.data.timestamp.values)), value = self.values))

    def update(self, updated_data):
        data = self.preprocess_dataframe(updated_data)
        values = SMA(data, self.period)

        new_value = values[-1]
        latest_timestamp = updated_data.iloc[-1].timestamp

        new_value_source = dict(
            timestamp=[latest_timestamp],
            value=[new_value]
        )

        self.cds.stream(new_value_source)
        self.values = np.append(self.values, [new_value])

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title='Simple Moving Average ({})'.format(self.period), x_range = plots[0].x_range)
                p.line(x="timestamp", y="value", source = self.cds, color=self.color, legend_label='SMA_{}'.format(self.period))
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(x="timestamp", y="value", source = self.cds, color=self.color, legend_label='SMA_{}'.format(self.period))
            
        return plots
