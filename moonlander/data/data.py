import time
import requests
import pandas as pd
import datetime as dt

from .helpers import resample_data

def binance_request_data(pair, interval, start = None, end = None):
    """Request historical data from Binance Exchange

    Parameters
    ----------
    symbol : str
        Trading pair
    interval : str
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

    start = int((start-dt.datetime(1970,1,1)).total_seconds() * 1000)
    end = int((end-dt.datetime(1970,1,1)).total_seconds() * 1000)

    # Grab the close tf possible given the dates
    url = "http://www.binance.com/api/v3/klines?symbol={0}&interval={1}&limit=1000&startTime={2}&endTime={3}"
    url = url.format(pair, interval, start, end)
    print(url)
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

    return df

def fetch_historical_binance(symbol, tf, start, end):
    """Fetch historical data for a coin pair from Binance

    Parameters
    ----------
    symbol : str
        Binance Exchange symbol
    tf : str
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

    # Handling of tf
    tf_s = tf.split("-")
    if len(tf_s) != 2:
        print("Available timeframes take the form of 'FREQ-UNIT'")
        print("Any timeframe above 5-MIN is available")
        print("E.g. 5-MIN, 12-HOUR, 3-DAY, 1-WEEK, 1-MONTH")

        raise ValueError("{0} is an invalid timeframe".format(tf))
    else:
        tf_1 = int(tf_s[0])
        tf_2 = str(tf_s[1])

        if tf_2 not in tf_mapper.keys():
            print("Try {0}".format(", ".join(tf_mapper.keys())))
            raise ValueError("{0} is an invalid unit of time...".format(tf_2))

    # Find closest compatible timeframe
    tf_secs = tf_to_secs(tf_1, tf_2)
    if tf_secs < 60:
        raise ValueError("Timeframe must be >= 1-MIN") 
    if tf_secs % 60 != 0:
        raise ValueError("Timeframe must be a multiple by 1-MIN")

    # Gets the compatible time frame yielding the most data
    tf_secs = [i for i in [60, 180, 300, 900, 1800, 3600, 7200, 14400, 21600, 28000, 43200, 86400, 259200, 604800, 2419200] if i <= tf_secs and tf_secs % i == 0][-1]
    interval = tfs_to_binance_interval(tf_secs)

    # Handling of dates
    start = dt.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')

    if end:
        end = dt.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
    else:
        end = dt.datetime.now()

    if start >= end:
        raise ValueError("Start date must be earlier than end date")

    # Get data
    df = binance_request_data(symbol, interval, start, end)

    # Resample to higher time frame if necessary
    df = resample_data(df, tf_1, tf_2)

    return df