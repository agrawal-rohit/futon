import pandas as pd
import warnings
from ..account import LocalAccount
import bokeh
import time
import numpy as np
from tqdm.auto import tqdm
from bokeh.layouts import gridplot
from ..viz import create_candle_plot

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

    def backtest(self, amount = 1000):
        tracker = []
        account = LocalAccount(amount)

        # Enter backtest ---------------------------------------------  
        for index, today in tqdm(self.data.iterrows(), total = self.data.shape[0]):
            date = today['timestamp']
            equity = account.total_value(today['close'])

            # Handle stop loss
            for p in account.positions:
                if p.type == "long":
                    if p.stop_hit(today['low']):
                        account.close_position(p, 1.0, today['low'])
                if p.type == "short":
                    if p.stop_hit(today['high']):
                        account.close_position(p, 1.0, today['high'])
            
            # Cleanup empty positions
            account.purge_positions()  
            
            # Update account variables
            account.date = date
            account.equity.append(equity)

            # Equity tracking
            tracker.append({'date': date, 
                                 'benchmark_equity' : today['close'],
                                 'strategy_equity' : equity})

            # Execute trading logic
            lookback = self.data[0:index+1]
            self.logic(account, lookback)

            # Cleanup empty positions
            account.purge_positions()  
        # ------------------------------------------------------------

        self.backtest_results(account)

    def backtest_results(self, account, plot_performance = True):
        print("-------------- Results ----------------\n")
        being_price = self.data.iloc[0]['open']
        final_price = self.data.iloc[-1]['close']

        pc = percent_change(being_price, final_price)
        print("Buy and Hold : {0}%".format(round(pc*100, 2)))
        print("Net Profit   : {0}".format(round(profit(account.initial_capital, pc), 2)))
        
        pc = percent_change(account.initial_capital, account.total_value(final_price))
        print("Strategy     : {0}%".format(round(pc*100, 2)))
        print("Net Profit   : {0}".format(round(profit(account.initial_capital, pc), 2)))

        longs  = len([t for t in account.opened_trades if t.type == 'long'])
        sells  = len([t for t in account.closed_trades if t.type == 'long'])
        shorts = len([t for t in account.opened_trades if t.type == 'short'])
        covers = len([t for t in account.closed_trades if t.type == 'short'])

        print("Longs        : {0}".format(longs))
        print("Sells        : {0}".format(sells))
        print("Shorts       : {0}".format(shorts))
        print("Covers       : {0}".format(covers))
        print("--------------------")
        print("Total Trades : {0}".format(longs + sells + shorts + covers))
        print("\n---------------------------------------")

        if plot_performance:
            self.chart(account, show_trades=True)

    def chart(self, account, show_trades=False, title="Equity Curve"):
        """Chart results.
        :param show_trades: Show trades on plot
        :type show_trades: bool
        :param title: Plot title
        :type title: str
        """     

        candle_plot, _ = create_candle_plot(self.asset, fig_height=300)

        p = bokeh.plotting.figure(x_axis_type="datetime", plot_width=1000, plot_height=300, title=title, x_range = candle_plot.x_range)
        p.grid.grid_line_alpha = 0.3
        p.xaxis.axis_label = 'Date'
        p.yaxis.axis_label = 'Equity'
        shares = account.initial_capital/self.data.iloc[0]['open']
        base_equity = [price*shares for price in self.data['close']]      
        p.line(self.data['timestamp'], base_equity, color='#CAD8DE', legend='Buy and Hold')
        p.line(self.data['timestamp'], account.equity, color='#49516F', legend='Strategy')
        p.legend.location = "top_left"

        if show_trades:
            for trade in account.opened_trades:
                try:
                    x = time.mktime(trade.date.timetuple())*1000
                    y = account.equity[np.where(self.data['timestamp'] == trade.date.strftime("%Y-%m-%d"))[0][0]]
                    if trade.type == 'long': 
                        p.circle(x, y, size=6, color='green', alpha=0.5)

                        long_pos = bokeh.models.Span(location=x,
                              dimension='height', line_color='green',
                              line_dash='dashed', line_width=3)
                        candle_plot.add_layout(long_pos)

                    elif trade.type == 'short': 
                        p.circle(x, y, size=6, color='red', alpha=0.5)
                except:
                    pass

            for trade in account.closed_trades:
                try:
                    x = time.mktime(trade.date.timetuple())*1000
                    y = account.equity[np.where(self.data['timestamp'] == trade.date.strftime("%Y-%m-%d"))[0][0]]
                    if trade.type == 'long': 
                        p.circle(x, y, size=6, color='blue', alpha=0.5)

                        long_pos = bokeh.models.Span(location=x,
                              dimension='height', line_color='red',
                              line_dash='dashed', line_width=3)
                        candle_plot.add_layout(long_pos)

                    elif trade.type == 'short': 
                        p.circle(x, y, size=6, color='orange', alpha=0.5)
                except:
                    pass
            
        return bokeh.plotting.show(gridplot([[p], [candle_plot]]))
