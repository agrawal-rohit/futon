class Provider:
    """
    Base class for a data provider
    """

    def __init__(self):
        pass

    def validate_asset_config(self, base_asset, quote_asset, timeframe):
        """
        Base method to validate asset configuration.
        """
        pass

    def fetch_valid_symbol(self, base_asset, quote_asset):
        """
        Base method to fetch valid symbol.
        """
        pass

    def fetch_historical_klines(self, save=True):
        """
        Base method to fetch historical klines.
        """
        pass
