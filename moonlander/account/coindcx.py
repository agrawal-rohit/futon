import hmac
import hashlib
import base64
import json
import time
import math
import requests

# Helpers
def truncate(number, digits):
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

class CoinDCX:
    def __init__(self, asset, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

        self.base_asset = asset.base_asset
        self.quote_asset = asset.quote_asset
        self.fetch_valid_symbol()

        # Fetch shares and balances
        self.update_shares_and_balances()

    def make_request(self, url, body):
        secret_bytes = bytes(self.api_secret, encoding='utf-8')

        json_body = json.dumps(body, separators = (',', ':'))
        signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }

        response = requests.post(url, data = json_body, headers = headers)
        return response.json();

    def fetch_valid_symbol(self):
        response = requests.get('https://api.coindcx.com/exchange/v1/markets_details')
        data = response.json()

        for details in data:
            if details['target_currency_short_name'] == self.base_asset and details['base_currency_short_name'] == self.quote_asset:
                self.symbol = details['symbol']
                self.pair = details['pair']
                return
                
        raise ValueError('No valid symbols exist for the pair ({}/{})'.format(self.base_asset, self.quote_asset))

    def update_shares_and_balances(self):
        body = {
            "timestamp": int(round(time.time() * 1000))
        }
        data = self.make_request("https://api.coindcx.com/exchange/v1/users/balances", body)

        for balance in data:
            if balance['currency'] == self.base_asset:
                self.shares = float(balance['balance'])
            
            if balance['currency'] == self.quote_asset:
                self.buying_power = float(balance['balance'])

    def buy(self, entry_capital, entry_price, stop_loss=0):
        entry_capital = float(entry_capital)
        
        if entry_capital < 0: 
            raise ValueError("Error: Entry capital must be positive")          
        elif entry_price < 0: 
            raise ValueError("Error: Entry price cannot be negative.")
        elif self.buying_power < entry_capital: 
            raise ValueError("Error: Not enough buying power to enter position")          
        else: 
            quantity = truncate(entry_capital / (entry_price), 1)

            body = {
                "side": "buy", 
                "order_type": "limit_order",
                "price_per_unit": entry_price,
                "market": self.symbol, 
                "total_quantity": quantity, 
                "timestamp": int(round(time.time() * 1000))
            }

            data = self.make_request("https://api.coindcx.com/exchange/v1/orders/create", body)
            if data.get('status') == 'error':
                raise RuntimeError('Could not place buy order!' + str(data.get('message')))

            print('Buy order placed sucessfully...')
            self.orders = data

    def sell(self, percent, current_price, stop_loss = math.inf):        
        if percent > 1 or percent < 0: 
            raise ValueError("Error: Percent must range between 0-1.")
        elif current_price < 0:
            raise ValueError("Error: Current price cannot be negative.")                      
        else: 
            quantity = truncate(self.shares * percent, 1) 

            body = {
                "side": "sell", 
                "order_type": "limit_order",
                "price_per_unit": current_price,
                "market": self.symbol, 
                "total_quantity": quantity, 
                "timestamp": int(round(time.time() * 1000))
            }

            data = self.make_request("https://api.coindcx.com/exchange/v1/orders/create", body)
            if data.get('status') == 'error':
                raise RuntimeError('Could not place sell order!' + str(data.get('message')))

            print('Sell order placed sucessfully...')
            self.orders = data
                        