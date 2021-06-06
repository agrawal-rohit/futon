from datetime import datetime, timedelta
import pandas as pd
import warnings
import bokeh
import time
import numpy as np
from tqdm.auto import tqdm

from bokeh.layouts import gridplot
from bokeh.io import show, push_notebook

from ..viz import create_candle_plot
from ..account.local import LocalAccount

def percent_change(d1, d2):
    return (d2 - d1) / d1

def profit(initial_capital, multiplier):
    return initial_capital * (multiplier + 1.0) - initial_capital

class TradingStrategyBase:
    def __init__(self, asset):
        if not isinstance(asset.data, pd.DataFrame):
            raise ValueError("Data must be a pandas dataframe")

        missing = set(['high', 'low', 'open', 'close', 'volume'])-set(asset.data.columns)
        if len(missing) > 0:
            msg = "Missing {0} column(s), dataframe must be HLOCV+".format(list(missing))
            warnings.warn(msg)

        self.asset = asset
        self.data = asset.data.reset_index()
        self.indicators = []

    def setup(self):
        pass

    def compute_indicators(self):
        # Compute values for all indicators
        for indicator in self.indicators:
            indicator.compute(self.data)

    def update_indicators(self):
        # Compute values for all indicators
        for indicator in self.indicators:
            indicator.update(self.data)
            indicator.lookback = indicator.values

    def backtest(self, amount = 1000, start_date = None, relative_lookback_size = None, commision = 0, verbose = False, plot_results = True, show_trades = True):
        tracker = []
        account = LocalAccount(amount, commision = commision, verbose = verbose)

        # Setting custom backtest sizes
        self.data = self.asset.data.reset_index()

        if start_date is not None:
            start_date_dt = pd.to_datetime(datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S'))
            self.data = self.asset.data.loc[start_date_dt:].reset_index()

        elif relative_lookback_size is not None:
            self.data = self.data.iloc[-relative_lookback_size:].reset_index(drop = True)

        self.setup()
        self.compute_indicators()

        print('Performing backtest from:', pd.to_datetime(self.data.timestamp.values[0]).strftime('%d %B, %Y (%H:%M:%S)'), 'to', pd.to_datetime(self.data.timestamp.values[-1]).strftime('%d %B, %Y (%H:%M:%S)'))

        # Enter backtest ---------------------------------------------  
        for index, today in tqdm(self.data.iterrows(), total = self.data.shape[0]):
            date = today['timestamp']
            equity = account.total_value(today['close'])

            # Handle stop loss
            for trade in account.trades:
                if trade.stop_hit(today['low']):
                    account.sell(1.0, today['low'])
            
            # Update account variables
            account.date = date
            account.equity.append(equity)

            # Equity tracking
            tracker.append({'date': date, 
                                 'benchmark_equity' : today['close'],
                                 'strategy_equity' : equity})

            # Execute trading logic
            lookback = self.data[0:index+1]

            # Get today's indicator values
            for indicator in self.indicators:
                indicator.lookback = indicator.values[0:index+1]

            self.logic(account, lookback)

        # ------------------------------------------------------------

        self.backtest_results(account, plot_results, show_trades)

    def backtest_results(self, account, plot_performance = True, show_trades = True):
        print("-------------- Results ----------------\n")
        being_price = self.data.iloc[0]['open']
        final_price = self.data.iloc[-1]['close']

        strategy_returns = percent_change(account.initial_capital, account.total_value(final_price))
        strategy_profit = profit(account.initial_capital, strategy_returns)
        buyhold_returns = percent_change(being_price, final_price)
        buyhold_profit = profit(account.initial_capital, buyhold_returns)

        print("Relative Returns: {0}%".format(round((strategy_returns - buyhold_returns) * 100, 2)))
        print("Relative Profit: {0}".format(round(strategy_profit - buyhold_profit, 2)))
        print()

        print("Strategy     : {0}%".format(round(strategy_returns*100, 2)))
        print("Net Profit   : {0}".format(round(strategy_profit, 2)))
        print()

        print("Buy and Hold : {0}%".format(round(buyhold_returns*100, 2)))
        print("Net Profit   : {0}".format(round(buyhold_profit, 2)))

        buys  = len([t for t in account.trades if t.type == 'buy'])
        sells  = len([t for t in account.trades if t.type == 'sell'])
        
        print()
        print("Buys        : {0}".format(buys))
        print("Sells        : {0}".format(sells))
        print("--------------------")
        print("Total Trades : {0}".format(buys + sells))
        print("\n---------------------------------------")

        if plot_performance:
            self.chart(account, show_trades=show_trades, colored= True)

    def chart(self, account, colored = False, show_positions=True, show_trades=True, title="Equity Curve"):
        """Chart results.
        :param show_trades: Show trades on plot
        :type show_trades: bool
        :param title: Plot title
        :type title: str
        """     

        # Plot candle plot
        self.candle_plot, _ = create_candle_plot(self.asset, fig_height=400, colored=colored)
        
        # Plot equity curve
        p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=title, x_range = self.candle_plot.x_range)
        p.grid.grid_line_alpha = 0.3
        p.xaxis.axis_label = 'Date'
        p.yaxis.axis_label = 'Equity'
        shares = account.initial_capital/self.data.iloc[0]['open']
        base_equity = [price*shares for price in self.data['close']]     

        p.line(self.data['timestamp'], base_equity, color='#CAD8DE', legend_label='Buy and Hold')
        p.line(self.data['timestamp'], account.equity, color='#49516F', legend_label='Strategy')
        p.legend.location = "top_left"

        final_plot_layout = [p]

        indicator_plots = [self.candle_plot]
        # Plot Indicators
        for indicator in self.indicators:
            indicator_plots = indicator.plot_indicator(indicator_plots)
        final_plot_layout += indicator_plots

        if show_positions:
            for position in account.positions:
                start = position.entry_date
                end = position.close_date

                final_plot_layout[0].add_layout(bokeh.models.BoxAnnotation(left=start, right=end, fill_alpha=0.1, fill_color='green', line_color='green', level="underlay"))
                final_plot_layout[1].add_layout(bokeh.models.BoxAnnotation(left=start, right=end, fill_alpha=0.1, fill_color='green', line_color='green', level="underlay"))


        if show_trades:
            for trade in account.trades:
                try:
                    y = account.equity[np.where(self.data['timestamp'] == trade.date)[0][0]]
                    if trade.type == 'buy': 
                        final_plot_layout[0].circle(trade.date, y, size=6, color='orange', alpha=0.5)

                        final_plot_layout[1].circle(trade.date, trade.price, size=8, color='orange', alpha=1, legend_label = 'Buy order')
                        # long_pos = bokeh.models.Span(location=trade.date,
                        #       dimension='height', line_color='green', line_alpha = 0.5,
                        #       line_dash='dashed', line_width=2)
                        # candle_plot.add_layout(long_pos)

                    elif trade.type == 'sell': 
                        final_plot_layout[0].circle(trade.date, y, size=6, color='blue', alpha=0.5)

                        final_plot_layout[1].circle(trade.date, trade.price, size=8, color='blue', alpha=1, legend_label = 'Sell order')
                        # long_pos = bokeh.models.Span(location=trade.date,
                        #       dimension='height', line_color='red', line_alpha = 0.5,
                        #       line_dash='dashed', line_width=2)
                        # candle_plot.add_layout(long_pos)

                except:
                    pass
            
        return bokeh.plotting.show(gridplot(final_plot_layout, ncols = 1))

    def execute(self, trading_account, max_data_points = 1000):
        self.asset.fetch_historical_data()
        self.data = self.asset.data.reset_index()

        self.setup()
        self.compute_indicators()

        candle_plot, volume_plot = create_candle_plot(self.asset, fig_height=400)
        # Inital plot with candles and indicators
        final_plot_layout = []

        indicator_plots = [candle_plot, volume_plot]

        # Plot Indicators
        for indicator in self.indicators:
            indicator_plots = indicator.plot_indicator(indicator_plots)
        final_plot_layout += indicator_plots

        stream_plot = show(gridplot(final_plot_layout, ncols = 1), notebook_handle = True)

        self.trading_account = trading_account

        def on_new_candle(candle):
            print('{} | Plotting new candle ...'.format(candle['timestamp']))
            print(candle)

            new_candle_dict=dict(
                timestamp=[candle['timestamp']],
                low=[candle['low']],
                high=[candle['high']],
                open=[candle['open']],
                close=[candle['close']],
                volume=[candle['volume']]
            )

            if candle['close'] > candle['open']:
                self.asset._data_source_increasing.stream(new_candle_dict)
            else:
                self.asset._data_source_decreasing.stream(new_candle_dict)


            new_scaling_source=dict(
                timestamp=[candle['timestamp']],
                low=[candle['low']],
                high=[candle['high']]
            )
            self.asset.scaling_source.stream(new_scaling_source)
            

            # Execute Live Trading Logic
            new_candle_row_dict = dict(
                timestamp = candle['timestamp'],
                low = candle['low'],
                high = candle['high'],
                open = candle['open'],
                close = candle['close'],
                volume = candle['volume']
            )
            
            self.data = self.data.append(new_candle_row_dict, ignore_index=True)
            self.data = self.data.iloc[-1000:]
            self.update_indicators()

            push_notebook(handle=stream_plot)

            self.trading_account.update_shares_and_balances()
            self.logic(self.trading_account, self.data)

        self.kline_stream = self.asset.provider.stream_klines(self.asset, new_candle_callback = on_new_candle)