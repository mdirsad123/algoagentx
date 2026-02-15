"""
DEPRECATED - Legacy trade statistics calculator

This file has been deprecated as the backtest engine now calculates
metrics internally. It remains for reference but should not be used.

For trade statistics, use the backtest engine's built-in metrics:
    engine/backtest_engine.py
"""

import sys

def main():
    print("⚠️  DEPRECATED: Trade statistics are now calculated by the backtest engine.")
    print("⚠️  Use engine/backtest_engine.py instead.")
    sys.exit(1)

if __name__ == "__main__":
    main()