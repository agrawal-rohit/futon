from moonlander.data import providers
import pandas as pd
import numpy as np
import datetime as dt
from math import pi
import json 

from . import data

from bokeh.plotting import figure, ColumnDataSource, show
from bokeh.layouts import gridplot
from bokeh.models import HoverTool, CustomJS, Range1d
from bokeh.events import Pan
from bokeh.io import show, push_notebook

import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time

class Asset:
    def __init__(self, base_asset, quote_asset, interval = '1-min', provider = 'Poloniex'):
        self.base_asset = base_asset.upper()
        self.quote_asset = quote_asset.upper()

        # Provider init
        self.provider = self.assign_provider(provider, interval)

        # Data
        self.data = None

        # Streaming
        self.latest_candle = None
        
    def __repr__(self):
        return 'Asset(base_asset={}, quote_asset={})'.format(self.currency, self.base_currency)

    def assign_provider(self, provider, interval):
        if provider == 'Poloniex':
            return data.providers.Poloniex(base_asset=self.base_asset, quote_asset=self.quote_asset, timeframe=interval)
        
        if provider == 'Binance':
            return data.providers.Binance(base_asset=self.base_asset, quote_asset=self.quote_asset, timeframe=interval)

    def fetch_historical_data(self, start, end = None):
        self.data = self.provider.fetch_historical_klines(start, end)

        inc = self.data.close > self.data.open
        dec = ~inc

        # Data sources for plotting
        self._data_source_increasing = ColumnDataSource(data=dict(date = list(self.data.index[inc]), open = self.data.open[inc].values, close = self.data.close[inc].values, high = self.data.high[inc].values, low = self.data.low[inc].values, volume = self.data.volume[inc].values))
        self._data_source_decreasing = ColumnDataSource(data=dict(date = list(self.data.index[dec]), open = self.data.open[dec].values, close = self.data.close[dec].values, high = self.data.high[dec].values, low = self.data.low[dec].values, volume = self.data.volume[dec].values))
        
        self.calculate_log_returns()

    def calculate_log_returns(self):
        self.data['log_returns'] = np.log(self.data.close / self.data.close.shift(1))
        
    def plot_candles(self, start = None, end = None, notebook_handle = False):
        if self.data is None:
            self.fetch_historical_data(start=start, end=end)

        INCREASING_COLOR = '#4CAF50'
        DECREASING_COLOR = '#F44336'

        p = figure(plot_width=1000, 
                plot_height=600, 
                x_axis_type="datetime", 
                y_axis_location="right", 
                tools="xpan,xwheel_zoom,reset,save",
                active_drag='xpan',
                active_scroll='xwheel_zoom',
                title="{}/{} | Candlestick plot".format(self.base_asset, self.quote_asset), 
                toolbar_location='above')
        
        p.grid.grid_line_alpha=0.3
        p.x_range.follow = "end"
        p.x_range.range_padding = 0
        p.x_range = Range1d(self._data_source_increasing.data['date'][-100], self._data_source_increasing.data['date'][-1])

        bar_width = self.provider.timeframe_seconds * 1000 * 0.6 # seconds in ms

        p.segment(x0='date', y0='high', x1='date', y1='low', source=self._data_source_increasing, color=INCREASING_COLOR)
        p.segment(x0='date', y0='high', x1='date', y1='low', source=self._data_source_decreasing, color=DECREASING_COLOR)

        p.vbar(x='date', width=bar_width, top='open', bottom='close', fill_color=INCREASING_COLOR, line_color=INCREASING_COLOR,
            source=self._data_source_increasing, name="price")
        p.vbar(x='date', width=bar_width, top='open', bottom='close', fill_color=DECREASING_COLOR, line_color=DECREASING_COLOR,
            source=self._data_source_decreasing, name="price")

        # Select specific tool for the plot
        price_hover = p.select(dict(type=HoverTool))

        # Choose, which glyphs are active by glyph name
        price_hover.names = ["price"]
        # Creating tooltips
        price_hover.tooltips = [("Date", "@date{%F}"),
                                 ("Open", "@open{$0,0.00000}"),
                                ("Close", "@close{$0,0.00000}"),
                            ("Volume", "@volume{($ 0.00000 a)}")]

        price_hover.formatters = {'@date': 'datetime'}

        p2 = figure(x_axis_type="datetime",  y_axis_location="right", tools="", toolbar_location=None, plot_width=1000, plot_height=200, x_range=p.x_range)
        p2.xaxis.major_label_orientation = pi/4
        
        p2.vbar(x='date', width = bar_width, top='volume', color=INCREASING_COLOR, source=self._data_source_increasing, alpha=0.5)
        p2.vbar(x='date', width = bar_width, top='volume', color=DECREASING_COLOR, source=self._data_source_decreasing, alpha=0.5)
            
        self.scaling_source = ColumnDataSource({'date': list(self.data.index), 'high': self.data.high.values, 'low': self.data.low.values})
        x_range_scaling_callback = CustomJS(args={'y_range': p.y_range, 'source': self.scaling_source}, code='''
            clearTimeout(window._autoscale_timeout);
            var Date = source.data.date,
                Low = source.data.low,
                High = source.data.high,
                start = cb_obj.start,
                end = cb_obj.end,
                min = Infinity,
                max = -Infinity;
            for (var i=0; i < Date.length; ++i) {
                if (start <= Date[i] && Date[i] <= end) {
                    max = Math.max(High[i], max);
                    min = Math.min(Low[i], min);
                }
            }
            var pad = (max - min) * .05;
            window._autoscale_timeout = setTimeout(function() {
                y_range.start = min - pad;
                y_range.end = max + pad;
            });
        ''')

        # Finalise the figure
        p.x_range.js_on_change('start', x_range_scaling_callback)
        self.scaling_source.js_on_change('data', x_range_scaling_callback)

        # TODO: Add x-range update based on data streaming
        # stream_data_inc_callback = CustomJS(args={'x_range': p.x_range, 'source': self._data_source_increasing}, code='''
        #     console.log(source.data['date'])
        #     x_range.start = source.data["date"][source.data["date"].length - 3]
        #     x_range.change.emit()
        # ''')

        # stream_data_dec_callback = CustomJS(args={'x_range': p.x_range, 'source': self._data_source_decreasing}, code='''
        #     console.log(source.data['date'])
        #     x_range.start = source.data["date"][source.data["date"].length - 3]
        #     x_range.change.emit()
        # ''')
        
        # self._data_source_increasing.js_on_change('stream', stream_data_inc_callback)
        # self._data_source_decreasing.js_on_change('stream', stream_data_dec_callback)

        return show(gridplot([[p], [p2]]), notebook_handle = notebook_handle)

    def plot_returns(self, kind="ts"):
        stock = ColumnDataSource(data=dict(open=[], close=[], high=[], low=[], index=[]))
        stock.data = stock.from_df(self.data)

        if kind == 'ts':
            p = figure(plot_width=800, plot_height=500, tools="xpan", toolbar_location=None, x_axis_type="datetime", title="{}/{} | Returns".format(self.base_asset, self.quote_asset))
            p.grid.grid_line_alpha=0.3
            p.line('date', 'log_returns', line_color="navy", source=stock)
            p.yaxis.axis_label = 'Returns'
            show(p)
            
        elif kind == 'hs':
            hist, edges = np.histogram(self.data.log_returns.dropna().values, bins=int(np.sqrt(len(self.data))))
            p = figure(plot_width=800, plot_height=500, tools="xpan", toolbar_location=None, x_axis_type="datetime", title="{}/{} | Frequency of returns".format(self.base_asset, self.quote_asset))
            p.grid.grid_line_alpha=0.3
            p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="navy", line_color="white")
            p.y_range.start = 0
            show(p)
            
    def mean_return(self, freq=None):
        if freq is None:
            # Daily returns
            return self.data.log_returns.mean()
        else:
            resampled_price = self.data.close.resample(freq).last()
            resampled_returns = np.log(resampled_price / resampled_price.shift(1))
            return resampled_returns.mean()
        
    def std_return(self, freq=None):
        if freq is None:
            # Daily std dev
            return self.data.log_returns.std()
        else:
            resampled_price = self.data.close.resample(freq).last()
            resampled_returns = np.log(resampled_price / resampled_price.shift(1))
            return resampled_returns.std()
        
    def annualized_perf(self):
        mean_return = round(self.mean_return('Y') * 100, 3)
        risk = round(self.std_return('Y') * 100, 3)
        print('Return: {}% | Risk: {}%'.format(mean_return, risk))

    def stream(self, max_data_points = 10000, debug = False):
        freq = self.provider.timeframe_to_binance_timeframe(self.provider.timeframe)

        new_candle_inc=dict(date=[], low=[], high=[], open=[], close=[], volume=[])
        new_candle_dec=dict(date=[], low=[], high=[], open=[], close=[], volume=[])
        new_scaling_source=dict(date=[], low=[], high=[])
        self.stream_plot = self.plot_candles(notebook_handle=True)

        def on_message(ws, message):
            message = json.loads(message)

            # TODO: Add live candle bar based on on WS ticker

            # If first candle or new candle received
            cleaned_timestamp = int(str(message['k']['T'])[:-3])
            current_timestamp = pd.to_datetime(dt.datetime.fromtimestamp(cleaned_timestamp))
            if self.latest_candle is None or current_timestamp > self.latest_candle['date']:

                if self.latest_candle is not None:
                    print('Plotting the recent complete candle')

                    if self.latest_candle['close'] > self.latest_candle['open']:
                        new_candle_inc['date'].append(self.latest_candle['date']) 
                        new_candle_inc['low'].append(self.latest_candle['low']) # prevent filling ram
                        new_candle_inc['high'].append(self.latest_candle['high'])  # prevent filling ram
                        new_candle_inc['open'].append(self.latest_candle['open'])  # prevent filling ram
                        new_candle_inc['close'].append(self.latest_candle['close'])  # prevent filling ram
                        new_candle_inc['volume'].append(self.latest_candle['volume'])  # prevent filling ram

                        self._data_source_increasing.stream(new_candle_inc, max_data_points)
                    else:
                        new_candle_dec['date'].append(self.latest_candle['date']) 
                        new_candle_dec['low'].append(self.latest_candle['low']) # prevent filling ram
                        new_candle_dec['high'].append(self.latest_candle['high'])  # prevent filling ram
                        new_candle_dec['open'].append(self.latest_candle['open'])  # prevent filling ram
                        new_candle_dec['close'].append(self.latest_candle['close'])  # prevent filling ram
                        new_candle_dec['volume'].append(self.latest_candle['volume'])  # prevent filling ram

                        self._data_source_decreasing.stream(new_candle_dec, max_data_points)

                    new_scaling_source['date'].append(self.latest_candle['date'])
                    new_scaling_source['low'].append(self.latest_candle['low'])
                    new_scaling_source['high'].append(self.latest_candle['high'])

                    self.scaling_source.stream(new_scaling_source, max_data_points)
                    
                    push_notebook(handle=self.stream_plot)

                print('{} | New candle received...'.format(current_timestamp))

            low = float(message['k']['l'])
            high = float(message['k']['h'])
            op = float(message['k']['o'])
            close = float(message['k']['c'])
            volume = float(message['k']['v'])   
            
            if message['k']['x'] == False:
                self.latest_candle = {
                    "date": current_timestamp,
                    "low": low,
                    "high": high,
                    "open": op,
                    "close": close,
                    "volume": volume
                }

        def on_error(ws):
            print(ws)

        def on_close(ws):
            print("### closed ###")

        def on_open(ws):
            print('Connection established...')

        websocket.enableTrace(debug)
        ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/{0}@kline_{1}".format(self.provider.symbol.lower(), freq),
                                on_open = on_open,
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)

        ws.run_forever()