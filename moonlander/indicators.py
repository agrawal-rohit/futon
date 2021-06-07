import bokeh
import numpy as np
import pandas as pd
from talib.abstract import *
import random

def get_color_list():
    return ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548', '#607D8B']

class Indicator:
    def __init__(self, plot = True, plot_separately = False, color = None):
        self.plot = plot
        self.plot_separately = plot_separately
        self.color = self.get_color(color)

    def get_color(self, color):
        if color is None:
            colors_list = get_color_list()
            return random.choice(colors_list)
        else:
            return color

    def preprocess_dataframe(self, data):
        cols = ['high', 'low', 'open', 'close', 'volume']
        HLOCV = {key: data[key].values for key in data if key in cols}
        return HLOCV

    def compute(self, data, plot = True):
        processed_data = self.preprocess_dataframe(data)
        self.values = self.compute_function(processed_data)

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(data.timestamp.values)), value = self.values))

    def update(self, updated_data, plot = True):
        processed_data = self.preprocess_dataframe(updated_data)
        values = self.compute_function(processed_data)

        new_value = values[-1]
        latest_timestamp = updated_data.iloc[-1].timestamp

        self.values = np.append(self.values, [new_value])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                value=[new_value]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=self.title, x_range = plots[0].x_range)
                p.line(x="timestamp", y="value", source = self.cds, color=self.color, line_width = 1, legend_label=self.legend_label)
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(x="timestamp", y="value", source = self.cds, color=self.color, line_width = 1, legend_label=self.legend_label)
            
        return plots

# ----------------------------------
# OVERLAP INDICATORS
# ----------------------------------

class BollingerBands(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'BBANDS_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Bollinger Bands({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return BBANDS(processed_data, **self.kwargs)

    def compute(self, data, plot = True):
        processed_data = self.preprocess_dataframe(data)
        self.upper, self.middle, self.lower = self.compute_function(processed_data)
        self.values = list(zip(self.upper, self.middle, self.lower))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(data.timestamp.values)), upper = self.upper, middle = self.middle, lower = self.lower))

    def update(self, updated_data, plot = True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_uppers, new_middles, new_lowers = self.compute_function(processed_data)

        new_upper = new_uppers[-1]
        new_middle = new_middles[-1]
        new_lower = new_lowers[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp
        self.upper = np.append(self.upper, [new_upper])
        self.middle = np.append(self.middle, [new_middle])
        self.lower = np.append(self.lower, [new_lower])

        self.values = np.append(self.values, [(new_upper, new_middle, new_lower)])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                upper=[new_upper],
                middle=[new_middle],
                lower=[new_lower]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=self.title, x_range = plots[0].x_range)
                p.add_layout(bokeh.models.Band(base='timestamp', lower='lower', upper='upper', source=self.cds, level='underlay', fill_color = self.color, 
                    fill_alpha=0.1, line_width=1, line_alpha = 1, line_color='black'))
                p.line(x="timestamp", y="middle", source = self.cds, color=self.color, line_alpha = 0.2, line_width = 1)
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].add_layout(bokeh.models.Band(base='timestamp', lower='lower', upper='upper', source=self.cds, level='underlay', fill_color = self.color,
                    fill_alpha=0.1, line_width=1, line_alpha = 1, line_color=self.color))
                plots[0].line(x="timestamp", y="middle", source = self.cds, color=self.color, line_alpha = 0.2, line_width = 1)

        return plots

class DoubleExponentialMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'DEMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Double Exponential Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return DEMA(processed_data, **self.kwargs)

class ExponentialMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'EMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Exponential Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return EMA(processed_data, **self.kwargs)

class HilbertTransformInstantaneousTrendline(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'HT-IT'
        self.title = 'Hilbert Transform - Instantaneous Trendline'

    def compute_function(self, processed_data):
        return HT_TRENDLINE(processed_data)

class KaufmanAdaptiveMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'KAMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Kaufman Adaptive Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return KAMA(processed_data, **self.kwargs)

class MovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'MA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return MA(processed_data, **self.kwargs)


class MESAAdaptiveMovingAverage(Indicator):
    def __init__(self, color = None, mama_color = None, fama_color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.mama_color = self.get_color(mama_color)
        self.fama_color = self.get_color(fama_color)
        self.legend_label = 'MAMA_{}-{}'.format(kwargs.get('fastlimit'), kwargs.get('slowlimit'))
        self.title = 'MESA Adaptive Moving Average (fastlimit = {}, slowlimit = {})'.format(kwargs.get('fastlimit'), kwargs.get('slowlimit'))

    def compute_function(self, processed_data):
        return MAMA(processed_data, **self.kwargs)

    def compute(self, data, plot = True):
        processed_data = self.preprocess_dataframe(data)
        self.mama, self.fama = self.compute_function(processed_data)
        self.values = list(zip(self.mama, self.fama))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(data.timestamp.values)), mama = self.mama, fama = self.fama))

    def update(self, updated_data, plot = True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_mamas, new_famas = self.compute_function(processed_data)

        new_mama = new_mamas[-1]
        new_fama = new_famas[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp
        self.mama = np.append(self.mama, [new_mama])
        self.fama = np.append(self.fama, [new_fama])

        self.values = np.append(self.values, [(new_mama, new_fama)])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                mama=[new_mama],
                fama=[new_fama]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=self.title, x_range = plots[0].x_range)
                p.line(x="timestamp", y="mama", source = self.cds, color=self.mama_color, line_width = 1)
                p.line(x="timestamp", y="fama", source = self.cds, color=self.fama_color, line_width = 1)
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(x="timestamp", y="mama", source = self.cds, color=self.mama_color, line_width = 1)
                plots[0].line(x="timestamp", y="fama", source = self.cds, color=self.fama_color, line_width = 1)

        return plots

class MidpointOverPeriod(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'MIDPOINT_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Midpoint over period ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return MIDPOINT(processed_data, **self.kwargs)

class MidpointPriceOverPeriod(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'MIDPRICE_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Midpoint Price over period ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return MIDPRICE(processed_data, **self.kwargs)

class ParabolicSAR(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'SAR_{}_{}'.format(kwargs.get('acceleration'), kwargs.get('maximum'))
        self.title = 'Parabolic SAR (accel = {}, max = {})'.format(kwargs.get('acceleration'), kwargs.get('maximum'))

    def compute_function(self, processed_data):
        return SAR(processed_data, **self.kwargs)

class ParabolicSARExtended(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'SAREXT'
        self.title = 'Parabolic SAR - Extended'

    def compute_function(self, processed_data):
        return SAREXT(processed_data, **self.kwargs)

class SimpleMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'SMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Simple Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return SMA(processed_data, **self.kwargs)

class TripleExponentialMovingAverageT3(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'T3_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Triple Exponential Moving Average - T3 ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return T3(processed_data, **self.kwargs)

class TripleExponentialMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'TEMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Triple Exponential Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return TEMA(processed_data, **self.kwargs)

class TriangularMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'TRIMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Triangular Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return TRIMA(processed_data, **self.kwargs)

class WeightedMovingAverage(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'WMA_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Weighted Moving Average ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return WMA(processed_data, **self.kwargs)

# ----------------------------------
# MOMENTUM INDICATORS
# ----------------------------------

class AverageDirectionalMovementIndex(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'ADX_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Average Directional Movement Index ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return ADX(processed_data, **self.kwargs)

class AverageDirectionalMovementIndexRating(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'ADXR_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Average Directional Movement Index Rating ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return ADXR(processed_data, **self.kwargs)

class AbsolutePriceOscillator(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'APO_{}'.format(kwargs.get('fastperiod'), kwargs.get('slowperiod'))
        self.title = 'Absolute Price Oscillator (fast = {}, slow = {})'.format(kwargs.get('fastperiod'), kwargs.get('slowperiod'))

    def compute_function(self, processed_data):
        return APO(processed_data, **self.kwargs)

class Aroon(Indicator):
    def __init__(self, color = None, aroondown_color = None, aroonup_color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.aroondown_color = self.get_color(aroondown_color)
        self.aroonup_color = self.get_color(aroonup_color)
        self.legend_label = 'AROON_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Aroon ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return AROON(processed_data, **self.kwargs)

    def compute(self, data, plot = True):
        processed_data = self.preprocess_dataframe(data)
        self.aroondown, self.aroonup = self.compute_function(processed_data)
        self.values = list(zip(self.aroondown, self.aroonup))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(data.timestamp.values)), aroondown = self.aroondown, aroonup = self.aroonup))

    def update(self, updated_data, plot = True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_aroondowns, new_aroonups = self.compute_function(processed_data)

        new_aroondown = new_aroondowns[-1]
        new_aroonup = new_aroonups[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp
        self.aroondown = np.append(self.aroondown, [new_aroondown])
        self.aroonup = np.append(self.aroonup, [new_aroonup])

        self.values = np.append(self.values, [(new_aroondown, new_aroonup)])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                aroondown=[new_aroondown],
                aroonup=[new_aroonup]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=self.title, x_range = plots[0].x_range)
                p.line(x="timestamp", y="aroondown", source = self.cds, color=self.aroondown_color, line_width = 1)
                p.line(x="timestamp", y="aroonup", source = self.cds, color=self.aroonup_color, line_width = 1)
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(x="timestamp", y="aroondown", source = self.cds, color=self.aroondown_color, line_width = 1)
                plots[0].line(x="timestamp", y="aroonup", source = self.cds, color=self.aroonup_color, line_width = 1)

        return plots

class AroonOscillator(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'AROONOSC_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Aroon Oscillator ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return AROONOSC(processed_data, **self.kwargs)

class BalanceOfPower(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'BOP'
        self.title = 'Balance Of Power'

    def compute_function(self, processed_data):
        return BOP(processed_data, **self.kwargs)

class CommodityChannelIndex(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'CCI_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Commodity Channel Index ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return CCI(processed_data, **self.kwargs)

class ChandeMomentumOscillator(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'CMO_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Chande Momentum Oscillator ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return CMO(processed_data, **self.kwargs)

class DirectionalMovementIndex(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'DX_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Directional Movement Index ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return DX(processed_data, **self.kwargs)

class RelativeStrengthIndex(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'RSI_{}'.format(kwargs.get('timeperiod'))
        self.title = 'Relative Strength Index ({})'.format(kwargs.get('timeperiod'))

    def compute_function(self, processed_data):
        return RSI(processed_data, **self.kwargs)

class StochasticOscillator(Indicator):
    def __init__(self, color = None, k_color = None, d_color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.k_color = self.get_color(k_color)
        self.d_color = self.get_color(d_color)
        self.legend_label = 'STOCH_{}_{}'.format(kwargs.get('slowk_period'), kwargs.get('slowd_period'))
        self.title = 'Stochastic Oscillator (k_period = {}, d_period = {})'.format(kwargs.get('slowk_period'), kwargs.get('slowd_period'))

    def compute_function(self, processed_data):
        return STOCH(processed_data, **self.kwargs)

    def compute(self, data, plot = True):
        processed_data = self.preprocess_dataframe(data)
        self.slowk, self.slowd = self.compute_function(processed_data)
        self.values = list(zip(self.slowk, self.slowd))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(data=dict(timestamp = list(pd.to_datetime(data.timestamp.values)), slowk = self.slowk, slowd = self.slowd))

    def update(self, updated_data, plot = True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_slowks, new_slowds = self.compute_function(processed_data)

        new_slowk = new_slowks[-1]
        new_slowd = new_slowds[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp

        self.slowk = np.append(self.slowk, [new_slowk])
        self.slowd = np.append(self.slowd, [new_slowd])

        self.values = np.append(self.values, [(new_slowk, new_slowd)])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                slowk=[new_slowk],
                slowd=[new_slowd]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=self.title, x_range = plots[0].x_range)
                p.line(x="timestamp", y="slowk", source = self.cds, color=self.k_color, line_width = 1, legend_label = '%K')
                p.line(x="timestamp", y="slowd", source = self.cds, color=self.d_color, line_width = 1, legend_label = '%D')
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(x="timestamp", y="slowk", source = self.cds, color=self.k_color, line_width = 1, legend_label = '%K')
                plots[0].line(x="timestamp", y="slowd", source = self.cds, color=self.d_color, line_width = 1, legend_label = '%D')

        return plots

class UltimateOscillator(Indicator):
    def __init__(self, color = None, plot = True, plot_separately = False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs
        
        # Plotting
        self.legend_label = 'ULTOSC_{}_{}_{}'.format(kwargs.get('timeperiod1'), kwargs.get('timeperiod2'), kwargs.get('timeperiod3'))
        self.title = 'Ultimate Oscillator (t1 = {}, t2 = {}, t3 = {})'.format(kwargs.get('timeperiod1'), kwargs.get('timeperiod2'), kwargs.get('timeperiod3'))

    def compute_function(self, processed_data):
        return ULTOSC(processed_data, **self.kwargs)

