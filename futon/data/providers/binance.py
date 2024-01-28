import requests
import datetime as dt
from .helpers import (
    datetime_to_timestamp,
    seconds_to_timeframe,
    validate_timeframe,
    timeframe_to_binance_timeframe,
    preprocess_timeframe,
    resample_data,
    timeframe_to_secs,
    minutes_of_new_data,
)
import pandas as pd
import os
import math
import json
from binance.client import Client
from binance import ThreadedWebsocketManager
import websocket
import threading
from . import Provider


class Binance(Provider):
    def __init__(self, api_key, api_secret):
        """
        Initialize the binance data provider by setting the correct credentials

        Parameters
        ----------
        api_key : str
            A binance API key (Create one here: https://www.binance.com/en-IN/my/settings/api-management)
        api_secret : str
            A binance API secret (Create one here: https://www.binance.com/en-IN/my/settings/api-management)
        """
        super().__init__(api_key, api_secret)
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.twm = ThreadedWebsocketManager(
            api_key=api_key, api_secret=api_secret
        )
        self.twm.start()

    def validate_asset_config(self, base_asset, quote_asset, timeframe):
        """
        Validate that a given instrument pair exists on the Binance exchange

        Parameters
        ----------
        base_asset : str
            Name of the asset to trade. For instance, base asset in 'BTC/USDT' would be BTC
        quote_asset : str
            Name of the asset to trade with. For instance, quote asset in 'BTC/USDT' would be USDT
        timeframe : str
            A 'futon' timeframe
        """
        self.fetch_valid_symbol(base_asset, quote_asset)

        self.timeframe = timeframe
        validate_timeframe(timeframe)
        self.timeframe_seconds = timeframe_to_secs(timeframe)

    def fetch_valid_symbol(self, base_asset, quote_asset):
        """
        Fetch the symbol for an instrument pair as stored on the Binance exchange

        Parameters
        ----------
        base_asset : str
            Name of the asset to trade. For instance, base asset in 'BTC/USDT' would be BTC
        quote_asset : str
            Name of the asset to trade with. For instance, quote asset in 'BTC/USDT' would be USDT
        """
        data = self.client.get_exchange_info()

        for symbol in data["symbols"]:
            if (
                symbol["baseAsset"] == base_asset
                and symbol["quoteAsset"] == quote_asset
            ):
                self.symbol = symbol["symbol"]
                return

        raise ValueError(
            "No valid symbols exist for the pair ({}/{})".format(
                base_asset, quote_asset
            )
        )

    def fetch_historical_klines(self, start_date, save=True):
        """
        Fetch the historical data from the Binance API for the current instrument pair

        Parameters
        ----------
        start_date : str, optional
            The starting date from which to fetch the historical data, by default None. If None, the earliest recorded date on the provider is taken.
            Acceptable format: 'year-month-day hour:minutes:seconds'
        save : bool, optional
            Whether to store the data as a local CSV file, by default True.
            (It is advised to keep this value as True to prevent fetching the entire data again on every run)

        Returns
        -------
        pandas.DataFrame
            A pandas.DataFrame containing the historical data in an OHLCV format
        """
        # Preprocess timeframe
        timeframe, timeframe_seconds = preprocess_timeframe(
            self.timeframe,
            valid_timeframes=[
                "1-min",
                "3-min",
                "5-min",
                "15-min",
                "30-min",
                "1-hour",
                "2-hour",
                "4-hour",
                "6-hour",
                "8-hour",
                "12-hour",
                "1-day",
                "3-day",
                "1-week",
                "1-month",
            ],
        )
        binance_timeframe = timeframe_to_binance_timeframe(timeframe)

        # Check for already existing hitorical data
        filename = "%s-%s-data.csv" % (self.symbol, binance_timeframe)
        if os.path.isfile(filename):
            data_df = pd.read_csv(
                filename, parse_dates=["timestamp"], index_col=["timestamp"]
            )
        else:
            data_df = pd.DataFrame()

        # Fetch the latest data
        oldest_point, newest_point = minutes_of_new_data(
            self.symbol,
            start_date,
            timeframe,
            data_df,
            source="binance",
            client=self.client,
        )
        delta_min = (newest_point - oldest_point).total_seconds() / 60
        bin_size = timeframe_seconds / 60
        available_data = math.ceil(delta_min / bin_size)

        if oldest_point == dt.datetime.strptime("1 Jan 2017", "%d %b %Y"):
            print(
                "Downloading all available %s data for %s. Be patient..!"
                % (binance_timeframe, self.symbol)
            )

        else:
            print(
                "Downloading %d minutes of data available for %s, i.e. %d instances of %s data."
                % (delta_min, self.symbol, available_data, binance_timeframe)
            )

        klines = self.client.get_historical_klines(
            self.symbol,
            binance_timeframe,
            oldest_point.strftime("%d %b %Y %H:%M:%S"),
            newest_point.strftime("%d %b %Y %H:%M:%S"),
        )
        data = pd.DataFrame(
            klines,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_av",
                "trades",
                "tb_base_av",
                "tb_quote_av",
                "ignore",
            ],
        )

        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        data.set_index("timestamp", inplace=True)
        data = data[["low", "high", "open", "close", "volume"]]

        data["low"] = data["low"].astype("float")
        data["high"] = data["high"].astype("float")
        data["open"] = data["open"].astype("float")
        data["close"] = data["close"].astype("float")
        data["volume"] = data["volume"].astype("float")

        if len(data_df) > 0:
            temp_df = pd.DataFrame(data)
            data_df = data_df.append(temp_df)
            data_df = data_df[~data_df.index.duplicated(keep="last")]
        else:
            data_df = data

        if save:
            data_df.to_csv(filename)

        print("All caught up..!")
        return data_df

    def stream_klines(self, asset, new_candle_callback):
        """
        Start a websocket connection and stream OHLCV candle data from the Binance exchange in real-time

        Parameters
        ----------
        asset : futon.instruments.Instrument
            An instance of the futon Instrument class
        new_candle_callback : function
            The callback function to call when a candle has closed
        """

        def handle_socket_message(ws, msg):
            """
            Callback function whenever a new tick is received from the websocket

            Parameters
            ----------
            ws : websocket instance
                Instance of the websocket
            msg : str
                A stringified json object containing the message sent along the tick
            """
            # If first candle or new candle received
            msg = json.loads(msg)

            cleaned_timestamp = int(str(msg["k"]["T"])[:-3])
            current_timestamp = pd.to_datetime(cleaned_timestamp, unit="s")
            low = float(msg["k"]["l"])
            high = float(msg["k"]["h"])
            op = float(msg["k"]["o"])
            close = float(msg["k"]["c"])
            volume = float(msg["k"]["v"])
            isFinished = msg["k"]["x"]

            current_candle = {
                "timestamp": current_timestamp,
                "low": low,
                "high": high,
                "open": op,
                "close": close,
                "volume": volume,
                "isFinished": isFinished,
            }

            if isFinished and current_timestamp not in asset.data.index:
                new_candle_callback(current_candle)

        binance_timeframe = self.timeframe_to_provider_timeframe(
            self.timeframe
        )
        websocket_url = "wss://stream.binance.com:9443/ws/{}@kline_{}".format(
            self.symbol.lower(), binance_timeframe
        )
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            websocket_url, on_message=handle_socket_message
        )

        ws.run_forever()
