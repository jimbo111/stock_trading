"""Feature engineering definitions and computation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List

# Feature columns will be populated by compute_features
FEATURE_COLUMNS: List[str] = []


def compute_returns(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    """Compute log returns over multiple periods."""
    result = pd.DataFrame(index=df.index)

    for period in periods:
        result[f'ret_{period}d'] = df.groupby(level='symbol')['close'].transform(
            lambda x: np.log(x / x.shift(period))
        )

    return result


def compute_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """Compute momentum features (returns skipping recent days)."""
    result = pd.DataFrame(index=df.index)
    close = df['close']

    # Momentum: skip last 5 days to avoid reversal
    for months, days in [(1, 21), (3, 63), (6, 126), (12, 252)]:
        result[f'mom_{months}m'] = close.groupby(level='symbol').transform(
            lambda x: np.log(x.shift(5) / x.shift(days))
        )

    # Short-term reversal (5-day)
    result['reversal_5d'] = close.groupby(level='symbol').transform(
        lambda x: np.log(x / x.shift(5))
    )

    return result


def compute_drawdown(df: pd.DataFrame, window: int = 60) -> pd.Series:
    """Compute drawdown from rolling maximum."""
    close = df['close']

    def calc_dd(x):
        roll_max = x.rolling(window, min_periods=1).max()
        return (x - roll_max) / roll_max

    return close.groupby(level='symbol').transform(calc_dd).rename('drawdown_60d')


def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Compute realized volatility (annualized)."""
    returns = df.groupby(level='symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )

    rv = returns.groupby(level='symbol').rolling(window, min_periods=10).std()
    rv = rv.droplevel(0) * np.sqrt(252)  # Annualize

    return rv.rename('rv_20d')


def compute_beta(df_stock: pd.DataFrame, df_benchmark: pd.DataFrame,
                 window: int = 252) -> pd.Series:
    """Compute rolling beta vs benchmark using OLS."""
    # Compute returns
    stock_ret = df_stock.groupby(level='symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    bench_ret = df_benchmark['close'].pct_change()
    
    # Align and compute rolling beta
    result = []
    for symbol in df_stock.index.get_level_values('symbol').unique():
        symbol_ret = stock_ret.loc[pd.IndexSlice[:, symbol], :]
        
        # Align on dates
        aligned = pd.DataFrame({
            'stock': symbol_ret.values,
            'bench': bench_ret.reindex(symbol_ret.index.get_level_values('as_of_date')).values
        })
        
        # Rolling OLS beta
        def calc_beta(y, x):
            if len(x) < 20 or x.std() == 0:
                return np.nan
            return np.cov(y, x)[0, 1] / np.var(x)
        
        rolling_beta = aligned.rolling(window).apply(
            lambda df: calc_beta(df['stock'].values, df['bench'].values) 
            if len(df) == window else np.nan,
            raw=False
        )
        
        result.append(pd.Series(
            rolling_beta['stock'].values,
            index=symbol_ret.index,
            name='beta_kospi_252d'
        ))
    
    return pd.concat(result)


def compute_idiosyncratic_vol(df: pd.DataFrame, beta_series: pd.Series,
                               df_benchmark: pd.DataFrame, window: int = 60) -> pd.Series:
    """Compute idiosyncratic volatility (residual from market model)."""
    stock_ret = df.groupby(level='symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    bench_ret = df_benchmark['close'].pct_change()
    
    result = []
    for symbol in df.index.get_level_values('symbol').unique():
        symbol_ret = stock_ret.loc[pd.IndexSlice[:, symbol], :]
        symbol_beta = beta_series.loc[pd.IndexSlice[:, symbol], :]
        
        dates = symbol_ret.index.get_level_values('as_of_date')
        market_ret = bench_ret.reindex(dates).values
        
        # Residual = actual return - beta * market return
        residuals = symbol_ret.values - symbol_beta.values * market_ret
        residuals_series = pd.Series(residuals, index=symbol_ret.index)
        
        # Rolling std of residuals
        idio_vol = residuals_series.rolling(window, min_periods=20).std() * np.sqrt(252)
        result.append(idio_vol)
    
    return pd.concat(result).rename('idio_vol_60d')


def compute_fx_features(df_fx: pd.DataFrame) -> pd.DataFrame:
    """Compute FX rate change features."""
    # Set date as index if not already
    if 'as_of_date' in df_fx.columns:
        df_fx = df_fx.set_index('as_of_date')

    result = pd.DataFrame(index=df_fx.index)

    usdkrw = df_fx[df_fx['currency_pair'] == 'USDKRW']['rate']

    result['fx_chg_5d'] = np.log(usdkrw / usdkrw.shift(5))
    result['fx_chg_20d'] = np.log(usdkrw / usdkrw.shift(20))

    return result


def compute_memory_features(df_memory: pd.DataFrame) -> pd.DataFrame:
    """Compute memory price change features."""
    # Set date as index if not already
    if 'as_of_date' in df_memory.columns:
        df_memory = df_memory.set_index('as_of_date')

    features = {}

    # Use DRAM_DDR4_8GB for DRAM, NAND_512GB for NAND
    dram_data = df_memory[df_memory['memory_type'].str.contains('DRAM')]['price_usd']
    nand_data = df_memory[df_memory['memory_type'].str.contains('NAND')]['price_usd']

    if len(dram_data) > 0:
        features['dram_chg_5d'] = np.log(dram_data / dram_data.shift(5))
        features['dram_chg_20d'] = np.log(dram_data / dram_data.shift(20))

    if len(nand_data) > 0:
        features['nand_chg_20d'] = np.log(nand_data / nand_data.shift(20))

    return pd.DataFrame(features)


def compute_sox_features(df_sox: pd.DataFrame) -> pd.DataFrame:
    """Compute SOX index change features."""
    result = pd.DataFrame(index=df_sox.index)
    
    result['sox_chg_5d'] = np.log(df_sox['close'] / df_sox['close'].shift(5))
    result['sox_chg_20d'] = np.log(df_sox['close'] / df_sox['close'].shift(20))
    
    return result


def compute_flow_features(df_flows: pd.DataFrame, df_prices: pd.DataFrame) -> pd.DataFrame:
    """Compute foreign flow features normalized by ADV."""
    # Calculate 60-day average daily value
    adv_60d = df_prices.groupby(level='symbol')['volume'].rolling(60, min_periods=20).mean()
    adv_60d = adv_60d.droplevel(0)

    # Align flows with ADV
    flows = df_flows.set_index(['as_of_date', 'symbol'])['net_flow']

    # Normalize by ADV
    foreign_flow_norm = flows / adv_60d

    return pd.DataFrame({'foreign_flow_norm': foreign_flow_norm})


def compute_turnover(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Compute rolling average turnover."""
    return df.groupby(level='symbol')['volume'].rolling(window, min_periods=10).mean().droplevel(0).rename('turnover_20d')


def expand_exports_with_decay(df_exports: pd.DataFrame, 
                               full_date_range: pd.DatetimeIndex,
                               half_life_days: int = 20) -> pd.DataFrame:
    """Expand monthly export data to daily with exponential decay."""
    # Assume exports reported monthly
    result = []
    
    for category in df_exports['category'].unique():
        cat_data = df_exports[df_exports['category'] == category].set_index('as_of_date')
        
        # Forward fill with exponential decay
        daily_values = []
        for date in full_date_range:
            # Find most recent export value
            past_values = cat_data[cat_data.index <= date]
            if len(past_values) == 0:
                daily_values.append(np.nan)
                continue
            
            last_value = past_values.iloc[-1]
            days_elapsed = (date - past_values.index[-1]).days

            # Apply exponential decay
            decay_factor = 0.5 ** (days_elapsed / half_life_days)
            # Use value_usd_millions if available, otherwise yoy_change
            value_col = 'value_usd_millions' if 'value_usd_millions' in cat_data.columns else 'yoy_change'
            decayed_value = last_value[value_col] * decay_factor
            
            daily_values.append(decayed_value)
        
        result.append(pd.DataFrame({
            'as_of_date': full_date_range,
            f'exports_{category}_yoy_decay': daily_values
        }))
    
    if result:
        return pd.concat([r.set_index('as_of_date') for r in result], axis=1)
    return pd.DataFrame()


def zscore_features(df: pd.DataFrame, window_min: int = 252) -> pd.DataFrame:
    """Z-score features using expanding window up to t-1."""
    result = pd.DataFrame(index=df.index)
    
    for col in df.columns:
        if df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
            # Expanding window z-score
            expanding = df.groupby(level='symbol')[col].expanding(min_periods=window_min)
            mean = expanding.mean().droplevel(0).shift(1)  # Shift to avoid leakage
            std = expanding.std().droplevel(0).shift(1)
            
            result[col] = (df[col] - mean) / (std + 1e-8)
            
            # Add missing flag
            result[f'{col}_missing'] = df[col].isna().astype(int)
    
    return result


def compute_features(
    df_prices: pd.DataFrame,
    df_fx: pd.DataFrame,
    df_memory: pd.DataFrame,
    df_exports: pd.DataFrame,
    df_flows: pd.DataFrame,
    df_benchmark: pd.DataFrame,
    df_sox: pd.DataFrame,
    zscore_window_min: int = 252,
    exports_decay_half_life: int = 20
) -> pd.DataFrame:
    """Compute all engineered features.
    
    Args:
        df_prices: Stock OHLCV data with MultiIndex [as_of_date, symbol]
        df_fx: FX rates data
        df_memory: Memory prices data
        df_exports: Korea exports data
        df_flows: KRX foreign flow data
        df_benchmark: KOSPI benchmark data
        df_sox: SOX index data
        zscore_window_min: Minimum window for z-scoring
        exports_decay_half_life: Half-life for export decay in days
        
    Returns:
        DataFrame with all engineered features, indexed by [as_of_date, symbol]
    """
    # Ensure proper MultiIndex
    if not isinstance(df_prices.index, pd.MultiIndex):
        df_prices = df_prices.set_index(['as_of_date', 'symbol'])
    
    features_list = []
    
    # Returns and momentum
    features_list.append(compute_returns(df_prices, [1, 5, 20]))
    features_list.append(compute_momentum(df_prices))
    features_list.append(compute_drawdown(df_prices, window=60))
    
    # Volatility and risk
    features_list.append(compute_volatility(df_prices, window=20))
    
    # Beta (simplified - would need proper alignment in production)
    # beta = compute_beta(df_prices, df_benchmark, window=252)
    # features_list.append(beta)
    
    # For now, create placeholder beta
    features_list.append(pd.Series(0.0, index=df_prices.index, name='beta_kospi_252d'))
    features_list.append(pd.Series(0.0, index=df_prices.index, name='idio_vol_60d'))
    
    # Turnover
    features_list.append(compute_turnover(df_prices, window=20))
    
    # Combine all features
    features_df = pd.concat(features_list, axis=1)
    
    # Broadcast scalar features to all symbols
    dates = df_prices.index.get_level_values('as_of_date').unique()
    
    # FX features (broadcast to all symbols)
    fx_feats = compute_fx_features(df_fx)
    for col in fx_feats.columns:
        features_df[col] = np.nan
        for date in dates:
            if date in fx_feats.index:
                features_df.loc[pd.IndexSlice[date, :], col] = fx_feats.loc[date, col]
    
    # Memory features (broadcast to all symbols)
    mem_feats = compute_memory_features(df_memory)
    for col in mem_feats.columns:
        features_df[col] = np.nan
        for date in dates:
            if date in mem_feats.index:
                features_df.loc[pd.IndexSlice[date, :], col] = mem_feats.loc[date, col]
    
    # SOX features (broadcast to all symbols)
    sox_feats = compute_sox_features(df_sox)
    for col in sox_feats.columns:
        features_df[col] = np.nan
        for date in dates:
            if date in sox_feats.index:
                features_df.loc[pd.IndexSlice[date, :], col] = sox_feats.loc[date, col]
    
    # Flow features
    flow_feats = compute_flow_features(df_flows, df_prices)
    features_df = features_df.join(flow_feats, how='left')
    
    # Export features with decay (broadcast to all symbols)
    export_feats = expand_exports_with_decay(
        df_exports, 
        pd.DatetimeIndex(dates),
        half_life_days=exports_decay_half_life
    )
    for col in export_feats.columns:
        features_df[col] = np.nan
        for date in dates:
            if date in export_feats.index:
                features_df.loc[pd.IndexSlice[date, :], col] = export_feats.loc[date, col]
    
    # Z-score all features
    features_df = zscore_features(features_df, window_min=zscore_window_min)
    
    # Update global feature list
    global FEATURE_COLUMNS
    FEATURE_COLUMNS = [c for c in features_df.columns if not c.endswith('_missing')]
    
    return features_df
