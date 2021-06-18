from peepop.brokers import Local
import unittest


class Methods(unittest.TestCase):
    def test_errors(self):
        a = Local(1000)
        self.assertRaises(ValueError, a.buy, 2000, 10)
        self.assertRaises(ValueError, a.buy, -500, 10)
        self.assertRaises(ValueError, a.buy, 500, -10)
        # Enter valid position
        a.buy(250, 10)
        self.assertRaises(ValueError, a.sell, 0.5, -20)
        self.assertRaises(ValueError, a.sell, 1.01, 20)
        self.assertRaises(ValueError, a.sell, -0.5, 20)

    def test_buy(self):
        a = Local(1000)

        # Win on a long
        a.buy(500, 10)
        a.buy(500, 10)
        self.assertEqual(a.buying_power, 0)
        self.assertEqual(a.total_value(10), 1000)

        a.sell(0.5, 20)
        self.assertEqual(a.buying_power, 1000)
        self.assertEqual(a.total_value(20), 2000)

        a.sell(1, 20)
        self.assertEqual(a.buying_power, 2000)

        # Lose on a long
        a.buy(1000, 50)
        a.sell(0.5, 25)
        self.assertEqual(a.buying_power, 1250)
        self.assertEqual(a.total_value(25), 1500)

    def test_decimals(self):
        # long with decimals
        a = Local(2)
        a.buy(1, 0.00000001)
        self.assertEqual(a.total_value(0.00000002), 3)
        a.sell(1, 0.00000002)
        self.assertEqual(a.buying_power, 3)

    def test_commision(self):
        # ten percent commission
        a = Local(1000, commision=0.01)
        a.buy(100, 20)
        self.assertEqual(a.buying_power, 900)
        self.assertEqual(a.total_value(25), 1022.52)

        a.sell(0.5, 30)
        self.assertEqual(a.buying_power, 973.51)
        self.assertEqual(a.total_value(25), 1034.77)

        a.sell(1.0, 50)
        self.assertEqual(a.buying_power, 1096.03)
        self.assertEqual(a.total_value(100), 1096.03)


if __name__ == "__main__":
    unittest.main()
