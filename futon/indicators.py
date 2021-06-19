import bokeh
import numpy as np
import pandas as pd
import talib.abstract as ta
import random


def get_color_list():
    return [
        "#F44336",
        "#E91E63",
        "#9C27B0",
        "#673AB7",
        "#3F51B5",
        "#2196F3",
        "#03A9F4",
        "#00BCD4",
        "#009688",
        "#4CAF50",
        "#8BC34A",
        "#CDDC39",
        "#FFEB3B",
        "#FFC107",
        "#FF9800",
        "#FF5722",
        "#795548",
        "#607D8B",
    ]


class Indicator:
    def __init__(self, plot=True, plot_separately=False, color=None):
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
        cols = ["high", "low", "open", "close", "volume"]
        HLOCV = {key: data[key].values for key in data if key in cols}
        return HLOCV

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.values = self.compute_function(processed_data)

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    value=self.values,
                )
            )

    def update(self, updated_data, plot=True):
        processed_data = self.preprocess_dataframe(updated_data)
        values = self.compute_function(processed_data)

        new_value = values[-1]
        latest_timestamp = updated_data.iloc[-1].timestamp

        self.values = np.append(self.values, [new_value])

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp], value=[new_value]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="value",
                    source=self.cds,
                    color=self.color,
                    line_width=1,
                    legend_label=self.legend_label,
                )
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="value",
                    source=self.cds,
                    color=self.color,
                    line_width=1,
                    legend_label=self.legend_label,
                )

        return plots


# ----------------------------------
# OVERLAP INDICATORS
# ----------------------------------


class BollingerBands(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "BBANDS_{}".format(kwargs.get("timeperiod"))
        self.title = "Bollinger Bands({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.BBANDS(processed_data, **self.kwargs)

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.upper, self.middle, self.lower = self.compute_function(
            processed_data
        )
        self.values = list(zip(self.upper, self.middle, self.lower))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    upper=self.upper,
                    middle=self.middle,
                    lower=self.lower,
                )
            )

    def update(self, updated_data, plot=True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_uppers, new_middles, new_lowers = self.compute_function(
            processed_data
        )

        new_upper = new_uppers[-1]
        new_middle = new_middles[-1]
        new_lower = new_lowers[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp
        self.upper = np.append(self.upper, [new_upper])
        self.middle = np.append(self.middle, [new_middle])
        self.lower = np.append(self.lower, [new_lower])

        self.values = np.append(
            self.values, [(new_upper, new_middle, new_lower)]
        )

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                upper=[new_upper],
                middle=[new_middle],
                lower=[new_lower],
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.add_layout(
                    bokeh.models.Band(
                        base="timestamp",
                        lower="lower",
                        upper="upper",
                        source=self.cds,
                        level="underlay",
                        fill_color=self.color,
                        fill_alpha=0.1,
                        line_width=1,
                        line_alpha=1,
                        line_color="black",
                    )
                )
                p.line(
                    x="timestamp",
                    y="middle",
                    source=self.cds,
                    color=self.color,
                    line_alpha=0.2,
                    line_width=1,
                )
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].add_layout(
                    bokeh.models.Band(
                        base="timestamp",
                        lower="lower",
                        upper="upper",
                        source=self.cds,
                        level="underlay",
                        fill_color=self.color,
                        fill_alpha=0.1,
                        line_width=1,
                        line_alpha=1,
                        line_color=self.color,
                    )
                )
                plots[0].line(
                    x="timestamp",
                    y="middle",
                    source=self.cds,
                    color=self.color,
                    line_alpha=0.2,
                    line_width=1,
                )

        return plots


class DoubleExponentialMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "DEMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Double Exponential Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.DEMA(processed_data, **self.kwargs)


class ExponentialMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "EMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Exponential Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.EMA(processed_data, **self.kwargs)


class HilbertTransformInstantaneousTrendline(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "HT-IT"
        self.title = "Hilbert Transform - Instantaneous Trendline"

    def compute_function(self, processed_data):
        return ta.HT_TRENDLINE(processed_data)


class KaufmanAdaptiveMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "KAMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Kaufman Adaptive Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.KAMA(processed_data, **self.kwargs)


class MovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MA_{}".format(kwargs.get("timeperiod"))
        self.title = "Moving Average ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.MA(processed_data, **self.kwargs)


class MESAAdaptiveMovingAverage(Indicator):
    def __init__(
        self,
        color=None,
        mama_color=None,
        fama_color=None,
        plot=True,
        plot_separately=False,
        **kwargs
    ):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.mama_color = self.get_color(mama_color)
        self.fama_color = self.get_color(fama_color)
        self.legend_label = "MAMA_{}-{}".format(
            kwargs.get("fastlimit"), kwargs.get("slowlimit")
        )
        self.title = "MESA Adaptive Moving Average (fastlimit = {}, slowlimit = {})".format(
            kwargs.get("fastlimit"), kwargs.get("slowlimit")
        )

    def compute_function(self, processed_data):
        return ta.MAMA(processed_data, **self.kwargs)

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.mama, self.fama = self.compute_function(processed_data)
        self.values = list(zip(self.mama, self.fama))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    mama=self.mama,
                    fama=self.fama,
                )
            )

    def update(self, updated_data, plot=True):
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
                timestamp=[latest_timestamp], mama=[new_mama], fama=[new_fama]
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="mama",
                    source=self.cds,
                    color=self.mama_color,
                    line_width=1,
                )
                p.line(
                    x="timestamp",
                    y="fama",
                    source=self.cds,
                    color=self.fama_color,
                    line_width=1,
                )
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="mama",
                    source=self.cds,
                    color=self.mama_color,
                    line_width=1,
                )
                plots[0].line(
                    x="timestamp",
                    y="fama",
                    source=self.cds,
                    color=self.fama_color,
                    line_width=1,
                )

        return plots


class MidpointOverPeriod(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MIDPOINT_{}".format(kwargs.get("timeperiod"))
        self.title = "Midpoint over period ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.MIDPOINT(processed_data, **self.kwargs)


class MidpointPriceOverPeriod(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MIDPRICE_{}".format(kwargs.get("timeperiod"))
        self.title = "Midpoint Price over period ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.MIDPRICE(processed_data, **self.kwargs)


class ParabolicSAR(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "SAR_{}_{}".format(
            kwargs.get("acceleration"), kwargs.get("maximum")
        )
        self.title = "Parabolic SAR (accel = {}, max = {})".format(
            kwargs.get("acceleration"), kwargs.get("maximum")
        )

    def compute_function(self, processed_data):
        return ta.SAR(processed_data, **self.kwargs)


class ParabolicSARExtended(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "SAREXT"
        self.title = "Parabolic SAR - Extended"

    def compute_function(self, processed_data):
        return ta.SAREXT(processed_data, **self.kwargs)


class SimpleMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "SMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Simple Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.SMA(processed_data, **self.kwargs)


class TripleExponentialMovingAverageT3(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "T3_{}".format(kwargs.get("timeperiod"))
        self.title = "Triple Exponential Moving Average - T3 ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.T3(processed_data, **self.kwargs)


class TripleExponentialMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "TEMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Triple Exponential Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.TEMA(processed_data, **self.kwargs)


class TriangularMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "TRIMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Triangular Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.TRIMA(processed_data, **self.kwargs)


class WeightedMovingAverage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "WMA_{}".format(kwargs.get("timeperiod"))
        self.title = "Weighted Moving Average ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.WMA(processed_data, **self.kwargs)


# ----------------------------------
# MOMENTUM INDICATORS
# ----------------------------------


class AverageDirectionalMovementIndex(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ADX_{}".format(kwargs.get("timeperiod"))
        self.title = "Average Directional Movement Index ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.ADX(processed_data, **self.kwargs)


class AverageDirectionalMovementIndexRating(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ADXR_{}".format(kwargs.get("timeperiod"))
        self.title = "Average Directional Movement Index Rating ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.ADXR(processed_data, **self.kwargs)


class AbsolutePriceOscillator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "APO_{}_{}".format(
            kwargs.get("fastperiod"), kwargs.get("slowperiod")
        )
        self.title = "Absolute Price Oscillator (fast = {}, slow = {})".format(
            kwargs.get("fastperiod"), kwargs.get("slowperiod")
        )

    def compute_function(self, processed_data):
        return ta.APO(processed_data, **self.kwargs)


class Aroon(Indicator):
    def __init__(
        self,
        color=None,
        aroondown_color=None,
        aroonup_color=None,
        plot=True,
        plot_separately=False,
        **kwargs
    ):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.aroondown_color = self.get_color(aroondown_color)
        self.aroonup_color = self.get_color(aroonup_color)
        self.legend_label = "AROON_{}".format(kwargs.get("timeperiod"))
        self.title = "Aroon ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.AROON(processed_data, **self.kwargs)

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.aroondown, self.aroonup = self.compute_function(processed_data)
        self.values = list(zip(self.aroondown, self.aroonup))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    aroondown=self.aroondown,
                    aroonup=self.aroonup,
                )
            )

    def update(self, updated_data, plot=True):
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
                aroonup=[new_aroonup],
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="aroondown",
                    source=self.cds,
                    color=self.aroondown_color,
                    line_width=1,
                )
                p.line(
                    x="timestamp",
                    y="aroonup",
                    source=self.cds,
                    color=self.aroonup_color,
                    line_width=1,
                )
                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="aroondown",
                    source=self.cds,
                    color=self.aroondown_color,
                    line_width=1,
                )
                plots[0].line(
                    x="timestamp",
                    y="aroonup",
                    source=self.cds,
                    color=self.aroonup_color,
                    line_width=1,
                )

        return plots


class AroonOscillator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "AROONOSC_{}".format(kwargs.get("timeperiod"))
        self.title = "Aroon Oscillator ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.AROONOSC(processed_data, **self.kwargs)


class BalanceOfPower(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "BOP"
        self.title = "Balance Of Power"

    def compute_function(self, processed_data):
        return ta.BOP(processed_data, **self.kwargs)


class CommodityChannelIndex(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "CCI_{}".format(kwargs.get("timeperiod"))
        self.title = "Commodity Channel Index ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.CCI(processed_data, **self.kwargs)


class ChandeMomentumOscillator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "CMO_{}".format(kwargs.get("timeperiod"))
        self.title = "Chande Momentum Oscillator ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.CMO(processed_data, **self.kwargs)


class DirectionalMovementIndex(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "DX_{}".format(kwargs.get("timeperiod"))
        self.title = "Directional Movement Index ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.DX(processed_data, **self.kwargs)


class MACD(Indicator):
    def __init__(
        self,
        color=None,
        macd_color=None,
        signal_color=None,
        plot=True,
        plot_separately=False,
        **kwargs
    ):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.macd_color = self.get_color(macd_color)
        self.signal_color = self.get_color(signal_color)
        self.legend_label = "MACD_{}_{}_{}".format(
            kwargs.get("fastperiod"),
            kwargs.get("slowperiod"),
            kwargs.get("signalperiod"),
        )
        self.title = "MACD (fastperiod = {}, slowperiod = {}, signalperiod = {})".format(
            kwargs.get("fastperiod"),
            kwargs.get("slowperiod"),
            kwargs.get("signalperiod"),
        )

    def compute_function(self, processed_data):
        return ta.MACD(processed_data, **self.kwargs)

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.macd, self.macdsignal, self.macdhist = self.compute_function(
            processed_data
        )
        self.values = list(zip(self.macd, self.macdsignal, self.macdhist))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    macd=self.macd,
                    macdsignal=self.macdsignal,
                    macdhist=self.macdhist,
                    zeros=[0] * len(self.macdhist),
                )
            )

            up = [True if val > 0 else False for val in self.macdhist]
            down = [True if val < 0 else False for val in self.macdhist]

            self.view_upper = bokeh.models.CDSView(
                source=self.cds, filters=[bokeh.models.BooleanFilter(up)]
            )
            self.view_lower = bokeh.models.CDSView(
                source=self.cds, filters=[bokeh.models.BooleanFilter(down)]
            )

    def update(self, updated_data, plot=True):
        processed_data = self.preprocess_dataframe(updated_data)
        new_macds, new_macdsignals, new_macdhists = self.compute_function(
            processed_data
        )

        new_macd = new_macds[-1]
        new_macdsignal = new_macdsignals[-1]
        new_macdhist = new_macdhists[-1]

        latest_timestamp = updated_data.iloc[-1].timestamp

        self.macd = np.append(self.macd, [new_macd])
        self.macdsignal = np.append(self.macdsignal, [new_macdsignal])
        self.macdhist = np.append(self.macdhist, [new_macdhist])

        self.values = np.append(
            self.values, [(new_macd, new_macdsignal, new_macdhist)]
        )

        if plot:
            new_value_source = dict(
                timestamp=[latest_timestamp],
                macd=[new_macd],
                macdsignal=[new_macdsignal],
                macdhist=[new_macdhist],
                zeros=[0],
            )

            self.cds.stream(new_value_source)

            up = [
                True if val > 0 else False for val in self.cds.data["macdhist"]
            ]
            down = [
                True if val < 0 else False for val in self.cds.data["macdhist"]
            ]

            self.view_upper = bokeh.models.CDSView(
                source=self.cds, filters=[bokeh.models.BooleanFilter(up)]
            )
            self.view_lower = bokeh.models.CDSView(
                source=self.cds, filters=[bokeh.models.BooleanFilter(down)]
            )

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="macd",
                    source=self.cds,
                    color=self.macd_color,
                    line_width=1,
                    legend_label="MACD",
                )
                p.line(
                    x="timestamp",
                    y="macdsignal",
                    source=self.cds,
                    color=self.signal_color,
                    line_width=1,
                    legend_label="Signal",
                )

                bar_width = (
                    (
                        self.cds.data["timestamp"][1]
                        - self.cds.data["timestamp"][0]
                    ).seconds
                    * 1000
                    * 0.6
                )
                p.vbar(
                    x="timestamp",
                    top="macdhist",
                    bottom="zeros",
                    width=bar_width,
                    color="#4CAF50",
                    fill_alpha=0.3,
                    source=self.cds,
                    view=self.view_upper,
                )
                p.vbar(
                    x="timestamp",
                    top="zeros",
                    bottom="macdhist",
                    width=bar_width,
                    color="#F44336",
                    fill_alpha=0.3,
                    source=self.cds,
                    view=self.view_lower,
                )

                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="macd",
                    source=self.cds,
                    color=self.macd_color,
                    line_width=1,
                    legend_label="MACD",
                )
                plots[0].line(
                    x="timestamp",
                    y="macdsignal",
                    source=self.cds,
                    color=self.signal_color,
                    line_width=1,
                    legend_label="Signal",
                )

                bar_width = (
                    (
                        self.cds.data["timestamp"][1]
                        - self.cds.data["timestamp"][0]
                    ).seconds
                    * 1000
                    * 0.6
                )
                plots[0].vbar(
                    x="timestamp",
                    top="macdhist",
                    bottom="zeros",
                    width=bar_width,
                    color="#4CAF50",
                    fill_alpha=0.3,
                    source=self.cds,
                    view=self.view_upper,
                )
                plots[0].vbar(
                    x="timestamp",
                    top="zeros",
                    bottom="macdhist",
                    width=bar_width,
                    color="#F44336",
                    fill_alpha=0.3,
                    source=self.cds,
                    view=self.view_lower,
                )

        return plots


class MoneyFlowIndex(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MFI_{}".format(kwargs.get("timeperiod"))
        self.title = "Money Flow Index ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.MFI(processed_data, **self.kwargs)


class MinusDirectionalIndicator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MINUS_DI_{}".format(kwargs.get("timeperiod"))
        self.title = "Minus Directional Indicator ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.MINUS_DI(processed_data, **self.kwargs)


class MinusDirectionalMovement(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MINUS_DM_{}".format(kwargs.get("timeperiod"))
        self.title = "Minus Directional Movement ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.MINUS_DM(processed_data, **self.kwargs)


class Momentum(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "MOM_{}".format(kwargs.get("timeperiod"))
        self.title = "Momentum ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.MOM(processed_data, **self.kwargs)


class PlusDirectionalIndicator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "PLUS_DI_{}".format(kwargs.get("timeperiod"))
        self.title = "Plus Directional Indicator ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.PLUS_DI(processed_data, **self.kwargs)


class PlusDirectionalMovement(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "PLUS_DM_{}".format(kwargs.get("timeperiod"))
        self.title = "Plus Directional Movement ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.PLUS_DM(processed_data, **self.kwargs)


class PercentagePriceOscillator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "PPO_{}_{}".format(
            kwargs.get("fastperiod"), kwargs.get("slowperiod")
        )
        self.title = "Percentage Price Oscillator (fastperiod = {}, slowperiod = {})".format(
            kwargs.get("fastperiod"), kwargs.get("slowperiod")
        )

    def compute_function(self, processed_data):
        return ta.PPO(processed_data, **self.kwargs)


class RateOfChange(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ROC_{}".format(kwargs.get("timeperiod"))
        self.title = "Rate of change ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.ROC(processed_data, **self.kwargs)


class RateOfChangePercentage(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ROCP_{}".format(kwargs.get("timeperiod"))
        self.title = "Rate of change percentage ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.ROCP(processed_data, **self.kwargs)


class RateOfChangeRatio(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ROCR_{}".format(kwargs.get("timeperiod"))
        self.title = "Rate of change ratio ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.ROCR(processed_data, **self.kwargs)


class RateOfChangeRatio100Scale(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ROCR100_{}".format(kwargs.get("timeperiod"))
        self.title = "Rate of change ratio 100 scale ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.ROCR100(processed_data, **self.kwargs)


class RelativeStrengthIndex(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "RSI_{}".format(kwargs.get("timeperiod"))
        self.title = "Relative Strength Index ({})".format(
            kwargs.get("timeperiod")
        )

    def compute_function(self, processed_data):
        return ta.RSI(processed_data, **self.kwargs)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="value",
                    source=self.cds,
                    color=self.color,
                    line_width=1,
                    legend_label=self.legend_label,
                )

                p.add_layout(
                    bokeh.models.Span(
                        location=50,
                        dimension="width",
                        line_color="black",
                        line_dash="dashed",
                        line_width=1,
                    )
                )

                p.add_layout(
                    bokeh.models.BoxAnnotation(
                        top=30, fill_alpha=0.1, fill_color="red"
                    )
                )
                p.add_layout(
                    bokeh.models.BoxAnnotation(
                        bottom=70, fill_alpha=0.1, fill_color="green"
                    )
                )

                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="value",
                    source=self.cds,
                    color=self.color,
                    line_width=1,
                    legend_label=self.legend_label,
                )

                plots[0].add_layout(
                    bokeh.models.Span(
                        location=50,
                        dimension="width",
                        line_color="black",
                        line_dash="dashed",
                        line_width=1,
                    )
                )

                plots[0].add_layout(
                    bokeh.models.BoxAnnotation(
                        top=30, fill_alpha=0.1, fill_color="red"
                    )
                )
                plots[0].add_layout(
                    bokeh.models.BoxAnnotation(
                        bottom=70, fill_alpha=0.1, fill_color="green"
                    )
                )

        return plots


class StochasticSlow(Indicator):
    def __init__(
        self,
        timeperiod=5,
        smoothk=3,
        smoothd=3,
        color=None,
        k_color=None,
        d_color=None,
        plot=True,
        plot_separately=False,
    ):
        super().__init__(plot, plot_separately, color)
        self.timeperiod = timeperiod
        self.smoothk = smoothk
        self.smoothd = smoothd

        # Plotting
        self.k_color = self.get_color(k_color)
        self.d_color = self.get_color(d_color)
        self.legend_label = "STOCH_{}_{}_{}".format(
            timeperiod, smoothk, smoothd
        )
        self.title = "Stochastic Oscillator Slow (timeperiod = {}, smoothk = {}, smoothd = {})".format(
            timeperiod, smoothk, smoothd
        )

    def compute_function(self, processed_data):
        return ta.STOCH(
            processed_data,
            fastk_period=self.timeperiod,
            slowk_period=self.smoothk,
            slowd_period=self.smoothd,
        )

    def compute(self, data, plot=True):
        processed_data = self.preprocess_dataframe(data)
        self.slowk, self.slowd = self.compute_function(processed_data)
        self.values = list(zip(self.slowk, self.slowd))

        if plot:
            self.cds = bokeh.plotting.ColumnDataSource(
                data=dict(
                    timestamp=list(pd.to_datetime(data.timestamp.values)),
                    slowk=self.slowk,
                    slowd=self.slowd,
                )
            )

    def update(self, updated_data, plot=True):
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
                slowd=[new_slowd],
            )

            self.cds.stream(new_value_source)

    def plot_indicator(self, plots):
        if self.plot:
            if self.plot_separately:
                p = bokeh.plotting.figure(
                    x_axis_type="datetime",
                    plot_width=1000,
                    plot_height=200,
                    title=self.title,
                    x_range=plots[0].x_range,
                )
                p.line(
                    x="timestamp",
                    y="slowk",
                    source=self.cds,
                    color=self.k_color,
                    line_width=1,
                    legend_label="%K",
                )
                p.line(
                    x="timestamp",
                    y="slowd",
                    source=self.cds,
                    color=self.d_color,
                    line_width=1,
                    legend_label="%D",
                )

                p.add_layout(
                    bokeh.models.Span(
                        location=50,
                        dimension="width",
                        line_color="black",
                        line_dash="dashed",
                        line_width=1,
                    )
                )

                p.add_layout(
                    bokeh.models.BoxAnnotation(
                        top=20, fill_alpha=0.1, fill_color="red"
                    )
                )
                p.add_layout(
                    bokeh.models.BoxAnnotation(
                        bottom=80, fill_alpha=0.1, fill_color="green"
                    )
                )

                plots.append(p)
            else:
                # Add to the candle stick plot
                plots[0].line(
                    x="timestamp",
                    y="slowk",
                    source=self.cds,
                    color=self.k_color,
                    line_width=1,
                    legend_label="%K",
                )
                plots[0].line(
                    x="timestamp",
                    y="slowd",
                    source=self.cds,
                    color=self.d_color,
                    line_width=1,
                    legend_label="%D",
                )

                plots[0].add_layout(
                    bokeh.models.Span(
                        location=50,
                        dimension="width",
                        line_color="black",
                        line_dash="dashed",
                        line_width=1,
                    )
                )

                plots[0].add_layout(
                    bokeh.models.BoxAnnotation(
                        top=20, fill_alpha=0.1, fill_color="red"
                    )
                )
                plots[0].add_layout(
                    bokeh.models.BoxAnnotation(
                        bottom=80, fill_alpha=0.1, fill_color="green"
                    )
                )

        return plots


class TRIX(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "TRIX_{}".format(kwargs.get("timeperiod"))
        self.title = (
            "1-day Rate-Of-Change (ROC) of a Triple Smooth EMA ({})".format(
                kwargs.get("timeperiod")
            )
        )

    def compute_function(self, processed_data):
        return ta.TRIX(processed_data, **self.kwargs)


class UltimateOscillator(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ULTOSC_{}_{}_{}".format(
            kwargs.get("timeperiod1"),
            kwargs.get("timeperiod2"),
            kwargs.get("timeperiod3"),
        )
        self.title = "Ultimate Oscillator (t1 = {}, t2 = {}, t3 = {})".format(
            kwargs.get("timeperiod1"),
            kwargs.get("timeperiod2"),
            kwargs.get("timeperiod3"),
        )

    def compute_function(self, processed_data):
        return ta.ULTOSC(processed_data, **self.kwargs)


class WilliamsR(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "WILLR_{}".format(kwargs.get("timeperiod"))
        self.title = "Williams %R ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        return ta.WILLR(processed_data, **self.kwargs)


class SuperTrend(Indicator):
    def __init__(self, color=None, plot=True, plot_separately=False, **kwargs):
        super().__init__(plot, plot_separately, color)
        self.kwargs = kwargs

        # Plotting
        self.legend_label = "ST_{}".format(kwargs.get("timeperiod"))
        self.title = "SuperTrend ({})".format(kwargs.get("timeperiod"))

    def compute_function(self, processed_data):
        data = pd.DataFrame(processed_data)
        data["tr0"] = abs(data.high - data.low)
        data["tr1"] = abs(data.high - data.close.shift(1))
        data["tr2"] = abs(data.low - data.close.shift(1))
        data["TR"] = round(data[["tr0", "tr1", "tr2"]].max(axis=1), 2)
        data["ATR"] = 0.00
        data["BUB"] = 0.00
        data["BLB"] = 0.00
        data["FUB"] = 0.00
        data["FLB"] = 0.00
        data["ST"] = 0.00

        # Calculating ATR
        for i, row in data.iterrows():
            if i == 0:
                data.loc[i, "ATR"] = 0.00
            else:
                data.loc[i, "ATR"] = (
                    (data.loc[i - 1, "ATR"] * 13) + data.loc[i, "TR"]
                ) / self.kwargs.get("timeperiod")

        data["BUB"] = round(
            ((data.high + data.low) / 2)
            + (self.kwargs.get("factor") * data["ATR"]),
            2,
        )
        data["BLB"] = round(
            ((data.high + data.low) / 2)
            - (self.kwargs.get("factor") * data["ATR"]),
            2,
        )

        for i, row in data.iterrows():
            if i == 0:
                data.loc[i, "FUB"] = 0.00
            else:
                if (data.loc[i, "BUB"] < data.loc[i - 1, "FUB"]) | (
                    data.loc[i - 1, "close"] > data.loc[i - 1, "FUB"]
                ):
                    data.loc[i, "FUB"] = data.loc[i, "BUB"]
                else:
                    data.loc[i, "FUB"] = data.loc[i - 1, "FUB"]

        for i, row in data.iterrows():
            if i == 0:
                data.loc[i, "FLB"] = 0.00
            else:
                if (data.loc[i, "BLB"] > data.loc[i - 1, "FLB"]) | (
                    data.loc[i - 1, "close"] < data.loc[i - 1, "FLB"]
                ):
                    data.loc[i, "FLB"] = data.loc[i, "BLB"]
                else:
                    data.loc[i, "FLB"] = data.loc[i - 1, "FLB"]

        for i, row in data.iterrows():
            if i == 0:
                data.loc[i, "ST"] = 0.00
            elif (data.loc[i - 1, "ST"] == data.loc[i - 1, "FUB"]) & (
                data.loc[i, "close"] <= data.loc[i, "FUB"]
            ):
                data.loc[i, "ST"] = data.loc[i, "FUB"]
            elif (data.loc[i - 1, "ST"] == data.loc[i - 1, "FUB"]) & (
                data.loc[i, "close"] > data.loc[i, "FUB"]
            ):
                data.loc[i, "ST"] = data.loc[i, "FLB"]
            elif (data.loc[i - 1, "ST"] == data.loc[i - 1, "FLB"]) & (
                data.loc[i, "close"] >= data.loc[i, "FLB"]
            ):
                data.loc[i, "ST"] = data.loc[i, "FLB"]
            elif (data.loc[i - 1, "ST"] == data.loc[i - 1, "FLB"]) & (
                data.loc[i, "close"] < data.loc[i, "FLB"]
            ):
                data.loc[i, "ST"] = data.loc[i, "FUB"]

        return data["ST"].values
