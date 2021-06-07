from datetime import datetime
import requests
import sys
import numpy as np
import pandas as pd

sys.path.append('..')
import moonlander
from moonlander.data.providers import Binance
from moonlander.strategy import TradingStrategy

# Define Providers
api_key = 'JUY2Z2R1Lwpgta6toGtB8ofCxpiSBEiqqHJM8rp4GCWzIy2kXFbERuvxB2dDD1Cj'
secret_key = 'hDv51FaiLDHEA7Al2zhuG9YlXoKmgntjvgZDofFKNis1hY27x4WXHoL1RIsf1e8F'
binance = Binance(api_key, secret_key)

# Define tradeable asset
coin = moonlander.core.Asset('DOGE', 'USDT', provider = binance, interval = '5-min', start_date = '2021-05-01 00:00:00')

# Strategy
class StochasticUltimateCombo(TradingStrategy):
    def setup(self):
        self.stoch = moonlander.indicators.StochasticOscillator(fastk_period=14, slowk_period=14, slowd_period=14, plot_separately=True)
        self.ultosc = moonlander.indicators.UltimateOscillator(timeperiod1 = 5, timeperiod2 = 13, timeperiod3 = 21, plot_separately=True)
        self.indicators = [self.stoch, self.ultosc]
    
    def logic(self, account, lookback):
        try:
            today = lookback.iloc[-1]
            
            stoch_today = self.stoch.lookback[-1][0]
            ultosc_today = self.ultosc.lookback[-1]
            
            # Buying
            buy_signal = (stoch_today < 25) and (ultosc_today < 40)
            sell_signal = (stoch_today > 65) and (ultosc_today > 55)
            
            if buy_signal:
                entry_price   = today.close
                entry_capital = account.buying_power
                account.buy(entry_capital=entry_capital, entry_price=entry_price)
                
            # Selling
            if sell_signal:
                exit_price = today.close
                account.sell(percent=1.0, current_price=exit_price)
                
        except Exception as e:
#             print('ERROR', e)
            pass

strat = StochasticUltimateCombo(coin)

# Enable live trading
coindcx_api_key = 'fcb1c800d0ee02c93ea14bf61517afa0194d5c695eec9792'
coindcx_api_secret = '3071e32a059b72505f7d261d95aacb1ba66ab8e4cf5e89214bf329b454196c4c'
coindcxaccount = moonlander.account.coindcx.CoinDCX(coin, coindcx_api_key, coindcx_api_secret)

if __name__ == '__main__':
    print(strat.execute(trading_account = coindcxaccount, plot = False))
