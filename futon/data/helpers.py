import datetime as dt
import pandas as pd
import requests

tf_mapper = {"min": "T", "hour": "H", "day": "D", "week": "W", "month": "M"}


def resample_data(df, timeframe):
    """Resample dataframe to a higher timeframe.

    Parameters
    ----------
    df : pandas.DataFrame
        An HLOCV pandas dataframe with a datetime index
    integer : int
        The frequency of the higher timeframe
    htf : str
        The period of the higher timeframe (e.g. 'MIN', 'HOUR', 'DAY', 'WEEK', "MONTH")

    Returns
    -------
    pandas.DataFrame
        A resampled pandas dataframe
    """

    timeframe_values = timeframe.split("-")
    tf_freq = int(timeframe_values[0])
    tf_size = str(timeframe_values[1])
    new_timeframe = str(tf_freq) + tf_mapper[tf_size]

    df["low"] = df.low.resample(new_timeframe).min()
    df["high"] = df.high.resample(new_timeframe).max()
    df["open"] = df.open.resample(new_timeframe).first()
    df["close"] = df.close.resample(new_timeframe).last()
    df["volume"] = df.volume.resample(new_timeframe).sum()

    return df.dropna()


def timeframe_to_secs(timeframe):
    """Convert a timeframe into its equivalent in seconds.

    Parameters
    ----------
    freq : int
        The frequency of the timeframe
    unit : str
        The period of the timeframe (e.g. 'MIN', 'HOUR', 'DAY', 'WEEK', "MONTH")

    Returns
    -------
    int
        A timeframe represented as seconds
    """

    timeframe_values = timeframe.split("-")
    tf_freq = int(timeframe_values[0])
    tf_size = str(timeframe_values[1])

    multiplier = {
        "min": 60,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
        "month": 18144000,
    }

    return tf_freq * multiplier[tf_size]


def datetime_to_timestamp(datetime):
    return (datetime - dt.datetime(1970, 1, 1)).total_seconds()


def seconds_to_timeframe(seconds):
    # Convert seconds to binance time intervals
    time_ints = ["min", "hour", "day", "week", "month"]
    interval_index = -1
    while True:
        if seconds < 60:
            break

        seconds = int(seconds / 60)
        interval_index += 1

    return "{}-{}".format(seconds, time_ints[interval_index])


def validate_timeframe(timeframe):
    timeframe_values = timeframe.split("-")

    if len(timeframe_values) != 2:
        print("Available timeframes take the form of 'freq-unit'")
        print("E.g. 5-min, 12-hour, 3-day, 1-week, 1-month")

        raise ValueError("'{0}' is an invalid timeframe".format(timeframe))
    else:
        tf_freq = int(timeframe_values[0])
        tf_size = str(timeframe_values[1])

        if tf_size not in tf_mapper.keys():
            print("Try {0}".format(", ".join(tf_mapper.keys())))
            raise ValueError(
                "{0} is an invalid unit of time...".format(tf_size)
            )


def preprocess_timeframe(timeframe, valid_timeframes):
    min_timeframe = valid_timeframes[0]

    # Find closest compatible timeframe
    current_tf_secs = timeframe_to_secs(timeframe)
    min_tf_secs = timeframe_to_secs(min_timeframe)

    if current_tf_secs < min_tf_secs:
        raise ValueError("Timeframe must be >= {}".format(min_timeframe))
    if current_tf_secs % min_tf_secs != 0:
        raise ValueError(
            "Timeframe must be a multiple by {}".format(min_timeframe)
        )

    # Gets the optimal time frame yielding the most data
    valid_timeframes_seconds = [
        timeframe_to_secs(tf) for tf in valid_timeframes
    ]
    optimal_seconds = [
        i
        for i in valid_timeframes_seconds
        if i <= current_tf_secs and current_tf_secs % i == 0
    ][-1]
    optimal_timeframe = seconds_to_timeframe(optimal_seconds)

    return optimal_timeframe, optimal_seconds


def minutes_of_new_data(
    symbol, start_date, kline_size, data, source, client=None
):
    # Get start date for data feetching
    if len(data) > 0:
        start = data.index[-1]
    elif start_date:
        start = pd.to_datetime(
            dt.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        )
    elif source == "binance" or source == "coindcx":
        start = dt.datetime.strptime("1 Jan 2017", "%d %b %Y")

    # Get end date for date fetching
    if source == "binance":
        end = pd.to_datetime(
            client.get_klines(symbol=symbol, interval=kline_size)[-1][0],
            unit="ms",
        )
    elif source == "coindcx":
        response = requests.get(
            "https://public.coindcx.com/market_data/candles?pair={}&interval={}".format(
                symbol, kline_size
            )
        )
        data = response.json()
        end = pd.to_datetime(data[-1]["time"])

    return start, end
