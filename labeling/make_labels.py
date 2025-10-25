"""Label generation for 20-day excess returns."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from stores.label_store import LabelStore
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def make_excess_return_labels(
    df_prices: pd.DataFrame,
    benchmark_col: str = 'close',
    horizon_days: int = 20
) -> pd.DataFrame:
    """Compute 20D excess return labels and binary up/down target.
    
    Args:
        df_prices: DataFrame with MultiIndex [as_of_date, symbol] and 'close' column
                   Should also include benchmark with a specific symbol (e.g., '^KS11')
        benchmark_col: Column name for prices (default 'close')
        horizon_days: Forward-looking period for returns
        
    Returns:
        DataFrame with columns: [er20, y_class]
        - er20: Excess return in decimal form (not percentage)
        - y_class: Binary label (1 for positive ER, 0 for negative)
    """
    logger.info(f"Computing {horizon_days}-day excess return labels")
    
    if not isinstance(df_prices.index, pd.MultiIndex):
        df_prices = df_prices.set_index(['as_of_date', 'symbol'])
    
    results = []
    
    # Get unique symbols (excluding benchmark)
    symbols = [s for s in df_prices.index.get_level_values('symbol').unique() 
               if not s.startswith('^')]
    
    # Get benchmark returns
    benchmark_symbol = '^KS11'  # KOSPI
    if benchmark_symbol not in df_prices.index.get_level_values('symbol'):
        logger.warning(f"Benchmark {benchmark_symbol} not found, using zero excess returns")
        benchmark_returns = pd.Series(0.0, index=df_prices.index.get_level_values('as_of_date').unique())
    else:
        benchmark_prices = df_prices.loc[pd.IndexSlice[:, benchmark_symbol], benchmark_col]
        benchmark_returns = benchmark_prices.pct_change(horizon_days).shift(-horizon_days)
        benchmark_returns.index = benchmark_returns.index.get_level_values('as_of_date')
    
    for symbol in symbols:
        logger.debug(f"Processing labels for {symbol}")
        
        # Get stock prices
        stock_prices = df_prices.loc[pd.IndexSlice[:, symbol], benchmark_col]
        
        # Compute forward returns
        forward_returns = stock_prices.pct_change(horizon_days).shift(-horizon_days)
        
        # Get dates for this symbol
        dates = stock_prices.index.get_level_values('as_of_date')
        
        # Compute excess returns
        excess_returns = forward_returns.values - benchmark_returns.reindex(dates).fillna(0).values
        
        # Create labels DataFrame
        labels_df = pd.DataFrame({
            'as_of_date': dates,
            'symbol': symbol,
            'er20': excess_returns,
            'y_class': (excess_returns > 0).astype(int)
        })
        
        results.append(labels_df)
    
    # Combine all symbols
    all_labels = pd.concat(results, ignore_index=True)
    all_labels = all_labels.set_index(['as_of_date', 'symbol'])
    
    # Remove rows with NaN (beginning and end of series)
    all_labels = all_labels.dropna()
    
    logger.info(f"Generated {len(all_labels)} labels")
    logger.info(f"Positive class ratio: {all_labels['y_class'].mean():.3f}")
    
    return all_labels


def load_config():
    """Load project configuration."""
    config_path = Path("config/default.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_sample_prices():
    """Load sample price data."""
    df = pd.read_csv("samples/data/market_prices.sample.csv")
    df['as_of_date'] = pd.to_datetime(df['as_of_date'])
    return df


def main():
    """Generate labels from price data."""
    parser = argparse.ArgumentParser(description="Generate labels")
    parser.add_argument("--use-samples", action="store_true",
                       help="Use sample data instead of production data")
    
    args = parser.parse_args()
    
    config = load_config()
    horizon = config['horizon_days']
    
    if args.use_samples:
        df_prices = load_sample_prices()
    else:
        # TODO: Load from production data sources
        logger.error("Production data loading not implemented. Use --use-samples flag.")
        return
    
    # Generate labels
    labels = make_excess_return_labels(
        df_prices=df_prices,
        horizon_days=horizon
    )
    
    logger.info(f"Label statistics:\n{labels.describe()}")
    
    # Write to label store
    store = LabelStore(config['paths']['gold'])
    latest_date = labels.index.get_level_values('as_of_date').max()
    store.write(labels, latest_date.strftime('%Y-%m-%d'))
    
    logger.info(f"Labels written to {config['paths']['gold']}")


if __name__ == "__main__":
    main()
