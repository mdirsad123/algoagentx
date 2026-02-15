class BaseStrategy:
    """
    Base class for all strategies.

    IMPORTANT:
    - Engine calls `generate()`
    - Strategy MUST return DataFrame with `Position` column
    """

    def __init__(self, df, **kwargs):
        # Store a copy of market data
        self.df = df.copy()

    def generate(self):
        """
        Must return DataFrame with:
        Position column:
            1  = LONG
            -1 = SHORT
            0  = FLAT
        """
        raise NotImplementedError("Strategy must implement generate()")
