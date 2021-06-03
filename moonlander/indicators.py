import bokeh
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

    # def iterate(self):
    #     self.today = self.values[self.today_idx + 1]
    #     self.today_idx += 1

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=title, x_range = plots[1].x_range)
                p.line(self.data['timestamp'], self.values, color=self.color, legend='SMA_{}'.format(self.period))
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[1].line(self.data['timestamp'], self.values, color=self.color, legend='SMA_{}'.format(self.period))
