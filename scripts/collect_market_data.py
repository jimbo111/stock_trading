"""Collect market data using Yahoo Finance API.

This script downloads historical price data for:
- Samsung Electronics (005930.KS)
- SK hynix (000660.KS)
- KOSPI Index (^KS11)
- SOX Index (^SOX)

Usage:
    python scripts/collect_market_data.py --days 365
    python scripts/collect_market_data.py --start 2022-01-01 --end 2024-12-31
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf


def collect_market_data(start_date: str, end_date: str, output_path: str = "data/bronze/market_prices.csv"):
    """Download market data from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        output_path: Output CSV file path
    """
    symbols = {
        '005930.KS': 'Samsung Electronics',
        '000660.KS': 'SK hynix',
        '^KS11': 'KOSPI Index',
        '^SOX': 'SOX Semiconductor Index'
    }

    print(f"📊 Collecting market data from {start_date} to {end_date}")
    print(f"Symbols: {list(symbols.keys())}")

    all_data = []

    for symbol, name in symbols.items():
        print(f"\n  Downloading {name} ({symbol})...", end=" ")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)

            if len(df) == 0:
                print(f"⚠️  No data found")
                continue

            # Rename columns to match our schema
            df = df.reset_index()
            df['symbol'] = symbol
            df = df.rename(columns={
                'Date': 'as_of_date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Select only required columns
            df = df[['as_of_date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]

            # Convert date to string format
            df['as_of_date'] = pd.to_datetime(df['as_of_date']).dt.strftime('%Y-%m-%d')

            all_data.append(df)
            print(f"✓ {len(df)} rows")

        except Exception as e:
            print(f"✗ Error: {e}")

    if not all_data:
        print("\n❌ No data collected!")
        return

    # Combine all data
    result = pd.concat(all_data, ignore_index=True)
    result = result.sort_values(['as_of_date', 'symbol'])

    # Save to CSV
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print(f"\n✅ Saved {len(result)} rows to {output_path}")
    print(f"   Date range: {result['as_of_date'].min()} to {result['as_of_date'].max()}")
    print(f"   Symbols: {result['symbol'].unique().tolist()}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Collect market data from Yahoo Finance")
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=365, help='Number of days to look back (default: 365)')
    parser.add_argument('--output', type=str, default='data/bronze/market_prices.csv', help='Output file path')

    args = parser.parse_args()

    # Determine date range
    if args.end:
        end_date = args.end
    else:
        end_date = datetime.now().strftime('%Y-%m-%d')

    if args.start:
        start_date = args.start
    else:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')

    collect_market_data(start_date, end_date, args.output)


if __name__ == '__main__':
    main()
