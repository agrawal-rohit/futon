from futon.data.helpers import *
import datetime as dt
import pandas as pd
import unittest


class Methods(unittest.TestCase):
    def test_validate_timeframe(self):
        try:
            validate_timeframe("2-min")
        except:
            self.assertTrue(True)

        try:
            validate_timeframe("2min")
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(str(e), "'2min' is an invalid timeframe")

        try:
            validate_timeframe("2-year")
        except Exception as e:
            self.assertTrue(isinstance(e, ValueError))
            self.assertEqual(str(e), "year is an invalid unit of time...")

    def test_timeframe_to_secs(self):
        a = timeframe_to_secs("2-min")
        self.assertEqual(a, 120)

        a = timeframe_to_secs("2-hour")
        self.assertEqual(a, 7200)

        a = timeframe_to_secs("2-day")
        self.assertEqual(a, 172800)

        a = timeframe_to_secs("2-week")
        self.assertEqual(a, 1209600)

        a = timeframe_to_secs("2-month")
        self.assertEqual(a, 5184000)

    def test_datetime_to_timestamp(self):
        day = dt.datetime.strptime("2000-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        timestamp = datetime_to_timestamp(day)
        self.assertEqual(timestamp, 946684800)
        self.assertTrue(isinstance(timestamp, int))

    def test_seconds_to_timeframe(self):
        a = seconds_to_timeframe(120)
        self.assertEqual(a, "2-min")

        a = seconds_to_timeframe(7200)
        self.assertEqual(a, "2-hour")

        a = seconds_to_timeframe(172800)
        self.assertEqual(a, "2-day")

        a = seconds_to_timeframe(1209600)
        self.assertEqual(a, "2-week")

        a = seconds_to_timeframe(5184000)
        self.assertEqual(a, "2-month")

    def test_resample_data(self):
        test_data = pd.read_csv(
            "tests/test_data.csv",
            parse_dates=["timestamp"],
            index_col=["timestamp"],
        )
        new_df = resample_data(test_data, "2-hour")
        hours_diff = (new_df.index[1] - new_df.index[0]).seconds / 3600
        self.assertEqual(hours_diff, 2)


if __name__ == "__main__":
    unittest.main()
