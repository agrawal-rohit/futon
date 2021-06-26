from futon.instruments import Crypto
from futon.data.providers import Binance
import datetime as dt
import unittest


class Methods(unittest.TestCase):
    def test_unsupported_pair(self):
        # Add your developer API keys here
        api_key = "random_api_key"
        secret_key = "random_api_secret"

        binance = Binance(api_key, secret_key)
        today = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            Crypto(
                "DOGE",
                "INR",
                provider=binance,
                interval="8-hour",
                start_date=today,
            )
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(
                str(e), "No valid symbols exist for the pair (DOGE/INR)"
            )

    def test_invalid_timeframe(self):
        # Add your developer API keys here
        api_key = "random_api_key"
        secret_key = "random_api_secret"

        binance = Binance(api_key, secret_key)
        today = dt.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        try:
            Crypto(
                "DOGE",
                "USDT",
                provider=binance,
                interval="5hours",
                start_date=today,
            )
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(str(e), "'5hours' is an invalid timeframe")

        try:
            Crypto(
                "DOGE",
                "USDT",
                provider=binance,
                interval="4-years",
                start_date=today,
            )
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(str(e), "years is an invalid unit of time...")


if __name__ == "__main__":
    unittest.main()
