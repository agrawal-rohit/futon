import pandas as pd
import warnings
import bokeh
import time
import numpy as np
from tqdm.auto import tqdm
from bokeh.layouts import gridplot

from ..viz import create_candle_plot
from ..account import LocalAccount

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

        # Plotting
        self.candle_plot, _ = create_candle_plot(self.asset, fig_height=400, colored=False)

    def setup(self):
        pass

    def backtest(self, amount = 1000):
        tracker = []
        account = LocalAccount(amount)

        self.setup()

        # Compute values for all indicators
        for indicator in self.indicators:
            indicator.compute(self.data)

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

        self.backtest_results(account)

    def backtest_results(self, account, plot_performance = True):
        print("-------------- Results ----------------\n")
        being_price = self.data.iloc[0]['open']
        final_price = self.data.iloc[-1]['close']

        strategy_returns = percent_change(account.initial_capital, account.total_value(final_price))
        buyhold_returns = percent_change(being_price, final_price)

        print("Relative performance: {0}%".format(round((strategy_returns - buyhold_returns) * 100 / buyhold_returns, 2)))
        print()

        print("Strategy     : {0}%".format(round(strategy_returns*100, 2)))
        print("Net Profit   : {0}".format(round(profit(account.initial_capital, strategy_returns), 2)))
        print()

        print("Buy and Hold : {0}%".format(round(buyhold_returns*100, 2)))
        print("Net Profit   : {0}".format(round(profit(account.initial_capital, buyhold_returns), 2)))

        buys  = len([t for t in account.trades if t.type == 'buy'])
        sells  = len([t for t in account.trades if t.type == 'sell'])
        
        print()
        print("Buys        : {0}".format(buys))
        print("Sells        : {0}".format(sells))
        print("--------------------")
        print("Total Trades : {0}".format(buys + sells))
        print("\n---------------------------------------")

        if plot_performance:
            self.chart(account, show_trades=True)

    def chart(self, account, show_positions=True, show_trades=True, title="Equity Curve"):
        """Chart results.
        :param show_trades: Show trades on plot
        :type show_trades: bool
        :param title: Plot title
        :type title: str
        """     

        # Plot equity curve
        p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=title, x_range = self.candle_plot.x_range)
        p.grid.grid_line_alpha = 0.3
        p.xaxis.axis_label = 'Date'
        p.yaxis.axis_label = 'Equity'
        shares = account.initial_capital/self.data.iloc[0]['open']
        base_equity = [price*shares for price in self.data['close']]     

        p.line(self.data['timestamp'], base_equity, color='#CAD8DE', legend='Buy and Hold')
        p.line(self.data['timestamp'], account.equity, color='#49516F', legend='Strategy')
        p.legend.location = "top_left"

        final_plot_layout = [p, self.candle_plot]

        # Plot Indicators
        for indicator in self.indicators:
            indicator.plot_indicator(final_plot_layout)

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
                        final_plot_layout[0].circle(trade.date, y, size=6, color='green', alpha=0.5)

                        final_plot_layout[1].circle(trade.date, trade.price, size=8, color='green', alpha=0.5, legend = 'Buy order')
                        # long_pos = bokeh.models.Span(location=trade.date,
                        #       dimension='height', line_color='green', line_alpha = 0.5,
                        #       line_dash='dashed', line_width=2)
                        # candle_plot.add_layout(long_pos)

                    elif trade.type == 'sell': 
                        final_plot_layout[0].circle(trade.date, y, size=6, color='red', alpha=0.5)

                        final_plot_layout[1].circle(trade.date, trade.price, size=8, color='red', alpha=0.5, legend = 'Sell order')
                        # long_pos = bokeh.models.Span(location=trade.date,
                        #       dimension='height', line_color='red', line_alpha = 0.5,
                        #       line_dash='dashed', line_width=2)
                        # candle_plot.add_layout(long_pos)

                except:
                    pass
            
        return bokeh.plotting.show(gridplot(final_plot_layout, ncols = 1))
