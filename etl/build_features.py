"""Feature engineering pipeline entrypoint."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from etl.feature_defs import compute_features
from stores.feature_store import FeatureStore
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def load_config():
    """Load project configuration."""
    config_path = Path("config/default.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_sample_data():
    """Load sample data for development/testing."""
    logger.info("Loading sample data")
    
    df_prices = pd.read_csv("samples/data/market_prices.sample.csv")
    df_prices['as_of_date'] = pd.to_datetime(df_prices['as_of_date'])
    
    df_fx = pd.read_csv("samples/data/fx_rates.sample.csv")
    df_fx['as_of_date'] = pd.to_datetime(df_fx['as_of_date'])
    
    df_memory = pd.read_csv("samples/data/memory_prices.sample.csv")
    df_memory['as_of_date'] = pd.to_datetime(df_memory['as_of_date'])
    
    df_exports = pd.read_csv("samples/data/kr_exports.sample.csv")
    df_exports['as_of_date'] = pd.to_datetime(df_exports['as_of_date'])
    
    df_flows = pd.read_csv("samples/data/krx_flows.sample.csv")
    df_flows['as_of_date'] = pd.to_datetime(df_flows['as_of_date'])
    
    # Extract benchmark and SOX from prices
    df_benchmark = df_prices[df_prices['symbol'] == '^KS11'].set_index('as_of_date')[['close']]
    df_sox = df_prices[df_prices['symbol'] == '^SOX'].set_index('as_of_date')[['close']]
    
    # Filter to actual stocks
    df_prices = df_prices[df_prices['symbol'].isin(['005930.KS', '000660.KS'])]
    
    return df_prices, df_fx, df_memory, df_exports, df_flows, df_benchmark, df_sox


def main():
    """Build features from raw data."""
    parser = argparse.ArgumentParser(description="Build features")
    parser.add_argument("--use-samples", action="store_true", 
                       help="Use sample data instead of production data")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    config = load_config()
    
    if args.use_samples:
        df_prices, df_fx, df_memory, df_exports, df_flows, df_benchmark, df_sox = load_sample_data()
    else:
        # TODO: Load from production data sources
        logger.error("Production data loading not implemented. Use --use-samples flag.")
        return
    
    logger.info("Computing features")
    features = compute_features(
        df_prices=df_prices,
        df_fx=df_fx,
        df_memory=df_memory,
        df_exports=df_exports,
        df_flows=df_flows,
        df_benchmark=df_benchmark,
        df_sox=df_sox,
        zscore_window_min=config['features']['zscore_window_min'],
        exports_decay_half_life=config['features']['exports_decay_half_life_days']
    )
    
    logger.info(f"Generated {len(features)} feature rows with {len(features.columns)} columns")
    logger.info(f"Features: {list(features.columns)}")
    
    # Write to feature store
    store = FeatureStore(config['paths']['gold'])

    # Use the max as_of_date from the features
    latest_date = features.index.get_level_values('as_of_date').max()
    store.write(features, latest_date.strftime('%Y-%m-%d'))
    
    logger.info(f"Features written to {config['paths']['gold']}")


if __name__ == "__main__":
    main()
