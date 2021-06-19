import requests
import datetime as dt
from .helpers import (
    datetime_to_timestamp,
    seconds_to_timeframe,
    validate_timeframe,
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


class Provider:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret


class Binance(Provider):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.twm = ThreadedWebsocketManager(
            api_key=api_key, api_secret=api_secret
        )
        self.twm.start()

    def validate_asset_config(self, base_asset, quote_asset, timeframe):
        self.fetch_valid_symbol(base_asset, quote_asset)

        self.timeframe = timeframe
        validate_timeframe(timeframe)
        self.timeframe_seconds = timeframe_to_secs(timeframe)

    def timeframe_to_provider_timeframe(self, timeframe):
        timeframe_values = timeframe.split("-")
        return timeframe_values[0] + timeframe_values[1][0]

    def fetch_valid_symbol(self, base_asset, quote_asset):
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
        binance_timeframe = self.timeframe_to_provider_timeframe(timeframe)

        filename = "%s-%s-data.csv" % (self.symbol, binance_timeframe)
        if os.path.isfile(filename):
            data_df = pd.read_csv(
                filename, parse_dates=["timestamp"], index_col=["timestamp"]
            )
        else:
            data_df = pd.DataFrame()

        oldest_point, newest_point = minutes_of_new_data(
            self.symbol,
            start_date,
            binance_timeframe,
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

    # def stream_klines(self, asset, new_candle_callback):

    #     def handle_socket_message(msg):
    #         # If first candle or new candle received
    #         print(msg)

    #         cleaned_timestamp = int(str(msg['k']['T'])[:-3])
    #         current_timestamp = pd.to_datetime(cleaned_timestamp, unit='s')
    #         low = float(msg['k']['l'])
    #         high = float(msg['k']['h'])
    #         op = float(msg['k']['o'])
    #         close = float(msg['k']['c'])
    #         volume = float(msg['k']['v'])
    #         isFinished = msg['k']['x']

    #         current_candle = {
    #             "timestamp": current_timestamp,
    #             "low": low,
    #             "high": high,
    #             "open": op,
    #             "close": close,
    #             "volume": volume,
    #             "isFinished": isFinished
    #         }

    #         if isFinished and current_timestamp not in asset.data.index:
    #             new_candle_callback(current_candle)

    #     binance_timeframe = self.timeframe_to_provider_timeframe(self.timeframe)
    #     return self.twm.start_kline_socket(callback=handle_socket_message, symbol=self.symbol, interval = binance_timeframe)

    def stream_klines(self, asset, new_candle_callback):
        def handle_socket_message(ws, msg):
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


# class CoinDCX(Provider):
#     def __init__(self, api_key, api_secret):
#         super().__init__(api_key, api_secret)

#     def validate_asset_config(self, base_asset, quote_asset, timeframe):
#         self.fetch_valid_symbol(base_asset, quote_asset)

#         self.timeframe = timeframe
#         validate_timeframe(timeframe)
#         self.timeframe_seconds = timeframe_to_secs(timeframe)

#     def timeframe_to_provider_timeframe(self, timeframe):
#         timeframe_values = timeframe.split('-')
#         return timeframe_values[0] + timeframe_values[1][0]

#     def fetch_valid_symbol(self, base_asset, quote_asset):
#         response = requests.get('https://api.coindcx.com/exchange/v1/markets_details')
#         data = response.json()

#         for details in data:
#             if details['target_currency_short_name'] == base_asset and details['base_currency_short_name'] == quote_asset:
#                 self.symbol = details['symbol']
#                 self.pair = details['pair']
#                 return

#         raise ValueError('No valid symbols exist for the pair ({}/{})'.format(base_asset, quote_asset))


#     def fetch_historical_klines(self, save = True):
#         # Preprocess timeframe
#         timeframe, timeframe_seconds = preprocess_timeframe(self.timeframe, valid_timeframes=['1-min', '3-min', '5-min', '15-min', '30-min', '1-hour', '2-hour', '4-hour', '6-hour', '8-hour', '12-hour', '1-day', '3-day', '1-week', '1-month'])
#         coindcx_timeframe = self.timeframe_to_provider_timeframe(timeframe)

#         filename = '%s-%s-data.csv' % (self.symbol, coindcx_timeframe)
#         if os.path.isfile(filename):
#             data_df = pd.read_csv(filename, parse_dates=['timestamp'], index_col=['timestamp'])
#         else:
#             data_df = pd.DataFrame()

#         oldest_point, newest_point = minutes_of_new_data(self.pair, coindcx_timeframe, data_df, source = "coindcx", client = None)
#         delta_min = (newest_point - oldest_point).total_seconds()/60
#         bin_size = timeframe_seconds / 60
#         available_data = math.ceil(delta_min / bin_size)

#         if oldest_point == dt.datetime.strptime('1 Jan 2017', '%d %b %Y'):
#             print('Downloading all available %s data for %s. Be patient..!' % (coindcx_timeframe, self.symbol))

#         else:
#             print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data.' % (delta_min, self.symbol, available_data, coindcx_timeframe))

#         # klines = self.client.get_historical_klines(self.symbol, coindcx_timeframe, oldest_point.strftime("%d %b %Y %H:%M:%S"), newest_point.strftime("%d %b %Y %H:%M:%S"))
#         # klines =
#         data = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])

#         data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
#         data.set_index('timestamp', inplace=True)
#         data = data[['low', 'high', 'open', 'close', 'volume']]

#         data["low"] = data['low'].astype('float')
#         data["high"] = data['high'].astype('float')
#         data["open"] = data['open'].astype('float')
#         data["close"] = data['close'].astype('float')
#         data["volume"] = data['volume'].astype('float')

#         if len(data_df) > 0:
#             temp_df = pd.DataFrame(data)
#             data_df = data_df.append(temp_df)
#         else:
#             data_df = data

#         if save:
#             data_df.to_csv(filename)

#         print('All caught up..!')
#         return data_df
