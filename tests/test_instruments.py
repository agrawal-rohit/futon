from futon.instruments.crypto import Crypto
from futon.data.providers.binance import Binance
import datetime as dt
import pandas as pd
import unittest


class Methods(unittest.TestCase):
    def test_unsupported_pair(self):
        # Add your developer API keys here
        test_data = pd.read_csv(
            "tests/test_data.csv",
            parse_dates=["timestamp"],
            index_col=["timestamp"],
        )
        today = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            Crypto(
                "DOGE",
                "INR",
                data_df=test_data,
                interval="8-hour",
                start_date=today,
            )
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(
                str(e), "No valid symbols exist for the pair (DOGE/INR)"
            )


if __name__ == "__main__":
    unittest.main()
