import requests
import datetime as dt
from .helpers import datetime_to_timestamp, seconds_to_timeframe, validate_timeframe, preprocess_timeframe, resample_data, timeframe_to_secs
import pandas as pd

class Provider:
    def __init__(self, base_asset, quote_asset, timeframe):
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        
        self.timeframe = timeframe
        validate_timeframe(timeframe)
        self.timeframe_seconds = timeframe_to_secs(timeframe)

class Poloniex(Provider):
    def __init__(self, base_asset, quote_asset, timeframe):
        super().__init__(base_asset, quote_asset, timeframe)
        self.symbol = self.fetch_valid_symbol()
        
    def fetch_valid_symbol(self, show_all = False):
        """Get valid pair symbol for Poloniex Exchange

        Parameters
        ----------
        show : bool, optional
            Pretty print data, by default False

        Returns
        -------
        list
            A list of trading pairs
        """    

        url = "https://poloniex.com/public?command=returnTicker"
        response = requests.get(url)
        data = response.json()
        tickers = [i for i in data]
        if show_all:
            print("Available Pairs:")
            print(tickers)

        test_symbol = self.base_asset + '_' + self.quote_asset
        for ticker in tickers:
            if ticker == test_symbol:
                return ticker
        
        raise ValueError('No valid symbols exist for the pair ({}/{})'.format(self.base_asset, self.quote_asset))
        

    def fetch_historical_klines(self, start, end = None):
        """Fetch historical data for a coin pair from Poloniex

        Parameters
        ----------
        base_asset : str
            Target asset to trade
        quote_asset : str
            Quote asset to trade with
        timeframe : str
            Candle timeframe
        start : datetime
            Date for beginning of data
        end : datetime
            Date for end of data

        Returns
        -------
        pandas.DataFrame
            A pandas dataframe of historical data
        """    

        # Preprocess timeframe
        _, timeframe_seconds = preprocess_timeframe(self.timeframe, valid_timeframes=['5-min', '15-min', '30-min', '2-hour', '4-hour', '24-hour'])

        # Handling of dates
        start = dt.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        
        if end is not None and type(end) is str:
            end = dt.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        else:
            end = dt.datetime.now()

        if start >= end:
            raise ValueError("Start date must be earlier than end date")

        start = datetime_to_timestamp(start)
        end = datetime_to_timestamp(end)

        # Get data
        url = "https://poloniex.com/public?command=returnChartData&currencyPair={0}&start={1}&end={2}&resolution=auto&period={3}"
        url = url.format(self.symbol, start, end, timeframe_seconds)
        response = requests.get(url)
        df = pd.DataFrame(response.json())

        # Format dataframe
        df['date'] = pd.to_datetime(df.date, unit='s')
        df = df.set_index(df.date, drop=True)
        df = df[['low', 'high', 'open', 'close', 'volume']]

        # Resample to higher time frame if necessary
        df = resample_data(df, self.timeframe)

        self.timeframe_seconds = (df.index[1] - df.index[0]).total_seconds()
        self.timeframe = seconds_to_timeframe(self.timeframe_seconds)

        return df

class Binance(Provider):
    def __init__(self, base_asset, quote_asset, timeframe):
        super().__init__(base_asset, quote_asset, timeframe)
        self.symbol = self.fetch_valid_symbol()
        
    def timeframe_to_binance_timeframe(self, timeframe):
        timeframe_values = timeframe.split('-')
        return timeframe_values[0] + timeframe_values[1][0]

    def fetch_valid_symbol(self, show_all = False):
        """Get valid pair symbol for Binance Exchange

        Parameters
        ----------
        show : bool, optional
            Pretty print data, by default False

        Returns
        -------
        list
            A list of trading pairs
        """    

        response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
        data = response.json()

        for symbol in data['symbols']:
            if symbol['baseAsset'] == self.base_asset and symbol['quoteAsset'] == self.quote_asset:
                return symbol['symbol']

        raise ValueError('No valid symbols exist for the pair ({}/{})'.format(self.base_asset, self.quote_asset))
        

    def fetch_historical_klines(self, start, end = None):
        """Fetch historical data for a coin pair from Binance

        Parameters
        ----------
        base_asset : str
            Target asset to trade
        quote_asset : str
            Quote asset to trade with
        timeframe : str
            Candle timeframe
        start : datetime
            Date for beginning of data
        end : datetime
            Date for end of data

        Returns
        -------
        pandas.DataFrame
            A pandas dataframe of historical data
        """    

        # Preprocess timeframe
        timeframe, _ = preprocess_timeframe(self.timeframe, valid_timeframes=['1-min', '3-min', '5-min', '15-min', '30-min', '1-hour', '2-hour', '4-hour', '6-hour', '8-hour', '12-hour', '1-day', '3-day', '1-week', '1-month'])
        binance_timeframe = self.timeframe_to_binance_timeframe(timeframe)

        # Handling of dates
        start = dt.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        
        if end is not None and type(end) is str:
            end = dt.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        else:
            end = dt.datetime.now()

        if start >= end:
            raise ValueError("Start date must be earlier than end date")

        start = int(datetime_to_timestamp(start)*1000)
        end = int(datetime_to_timestamp(end)*1000)

        # Grab the close tf possible given the dates
        url = "http://www.binance.com/api/v3/klines?symbol={0}&interval={1}&limit=1000&startTime={2}&endTime={3}"
        url = url.format(self.symbol, binance_timeframe, start, end)
        response = requests.get(url)
        df = pd.DataFrame(response.json())
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'date_close', 'QSA', 'num_trades', 'taker base asset vol', 'taker quote asset vol', 'ignore']

        # Format dataframe
        df['date'] = pd.to_datetime(df.date, unit='ms')
        df = df.set_index(df.date, drop=True)
        df = df[['low', 'high', 'open', 'close', 'volume']]
        df["low"] = df['low'].astype('float')
        df["high"] = df['high'].astype('float')
        df["open"] = df['open'].astype('float')
        df["close"] = df['close'].astype('float')
        df["volume"] = df['volume'].astype('float')

        # Resample to higher time frame if necessary
        df = resample_data(df, self.timeframe)

        self.timeframe_seconds = (df.index[1] - df.index[0]).total_seconds()
        self.timeframe = seconds_to_timeframe(self.timeframe_seconds)

        return df

