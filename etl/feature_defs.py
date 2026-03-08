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
    """Compute rolling beta vs benchmark using vectorized rolling cov/var.

    Args:
        df_stock: Stock OHLCV data with MultiIndex [as_of_date, symbol].
        df_benchmark: Benchmark data with DatetimeIndex and 'close' column.
        window: Rolling window length in trading days.

    Returns:
        Series with same MultiIndex as df_stock, named 'beta_kospi_252d'.
        NaN is expected for the first ``window`` observations of each symbol.
    """
    # Log returns for each stock (MultiIndex Series)
    stock_ret = df_stock.groupby(level='symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )

    # Benchmark log returns on a plain DatetimeIndex
    bench_ret = np.log(df_benchmark['close'] / df_benchmark['close'].shift(1))

    result: list[pd.Series] = []
    for symbol in df_stock.index.get_level_values('symbol').unique():
        # Slicing a MultiIndex Series by a scalar key on the second level yields
        # a plain DatetimeIndex (the symbol level is consumed).  We work in that
        # flat space and rebuild the MultiIndex at the end.
        sym_ret: pd.Series = stock_ret.loc[pd.IndexSlice[:, symbol]]
        sym_dates: pd.DatetimeIndex = sym_ret.index  # plain DatetimeIndex here

        # Align benchmark to this symbol's dates (NaN where no benchmark obs)
        bench_aligned: pd.Series = bench_ret.reindex(sym_dates)

        # Vectorized rolling beta = Cov(stock, bench) / Var(bench)
        combined = pd.DataFrame(
            {'s': sym_ret.values, 'b': bench_aligned.values},
            index=sym_dates,
        )
        roll = combined.rolling(window, min_periods=max(20, window // 5))
        rolling_cov = roll['s'].cov(combined['b'])  # Series on DatetimeIndex
        rolling_var = roll['b'].var()

        beta_vals = rolling_cov / rolling_var

        # Restore the original MultiIndex so that pd.concat produces a
        # consistent [as_of_date, symbol] MultiIndex across all symbols.
        mi = pd.MultiIndex.from_arrays(
            [sym_dates, [symbol] * len(sym_dates)],
            names=['as_of_date', 'symbol'],
        )
        result.append(pd.Series(beta_vals.values, index=mi, name='beta_kospi_252d'))

    return pd.concat(result)


def compute_idiosyncratic_vol(df: pd.DataFrame, beta_series: pd.Series,
                               df_benchmark: pd.DataFrame, window: int = 60) -> pd.Series:
    """Compute idiosyncratic volatility (annualised rolling std of market-model residuals).

    Args:
        df: Stock OHLCV data with MultiIndex [as_of_date, symbol].
        beta_series: Rolling beta Series produced by ``compute_beta``, same MultiIndex.
        df_benchmark: Benchmark data with DatetimeIndex and 'close' column.
        window: Rolling window for residual volatility in trading days.

    Returns:
        Series with same MultiIndex as df, named 'idio_vol_60d'.
        NaN is expected wherever beta is NaN or during early rolling periods.
    """
    stock_ret = df.groupby(level='symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    # Log returns for benchmark on plain DatetimeIndex
    bench_ret = np.log(df_benchmark['close'] / df_benchmark['close'].shift(1))

    result: list[pd.Series] = []
    for symbol in df.index.get_level_values('symbol').unique():
        # Scalar key slice on second level → plain DatetimeIndex (symbol consumed)
        sym_ret: pd.Series = stock_ret.loc[pd.IndexSlice[:, symbol]]
        sym_beta: pd.Series = beta_series.loc[pd.IndexSlice[:, symbol]]
        sym_dates: pd.DatetimeIndex = sym_ret.index

        market_ret = bench_ret.reindex(sym_dates).values

        # Residual = stock return - beta * market return
        residuals = sym_ret.values - sym_beta.values * market_ret
        residuals_series = pd.Series(residuals, index=sym_dates)

        # Rolling annualised idiosyncratic volatility
        idio_vol_vals = (
            residuals_series.rolling(window, min_periods=20).std() * np.sqrt(252)
        )

        # Restore MultiIndex
        mi = pd.MultiIndex.from_arrays(
            [sym_dates, [symbol] * len(sym_dates)],
            names=['as_of_date', 'symbol'],
        )
        result.append(pd.Series(idio_vol_vals.values, index=mi, name='idio_vol_60d'))

    return pd.concat(result)


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
    """Expand monthly export data to daily with exponential decay.

    Replaces the O(dates × categories) Python loop with vectorised
    ``reindex`` + ``ffill`` followed by a vectorised decay calculation.

    Args:
        df_exports: Monthly export data with 'category', 'as_of_date', and
            either 'value_usd_millions' or 'yoy_change' columns.
        full_date_range: Target daily DatetimeIndex to expand into.
        half_life_days: Half-life for the exponential decay kernel (days).

    Returns:
        DataFrame indexed by ``full_date_range`` with one column per export
        category, named ``exports_{category}_yoy_decay``.
        NaN where no prior observation exists for a category.
    """
    decay_lambda = np.log(2) / half_life_days  # so decay = exp(-lambda * days)

    result_cols: dict[str, pd.Series] = {}

    for category in df_exports['category'].unique():
        cat_data = (
            df_exports[df_exports['category'] == category]
            .set_index('as_of_date')
            .sort_index()
        )

        value_col = (
            'value_usd_millions'
            if 'value_usd_millions' in cat_data.columns
            else 'yoy_change'
        )
        monthly_vals: pd.Series = cat_data[value_col]

        # Step 1: reindex to full_date_range — inserts NaN on non-report days
        daily = monthly_vals.reindex(full_date_range)

        # Step 2: track the last observation date using ffill on a helper index
        # Build a Series of "report dates" where values exist, NaN elsewhere
        report_dates = pd.Series(
            np.where(daily.notna(), daily.index, pd.NaT),
            index=full_date_range,
            dtype='datetime64[ns]',
        )
        # Forward-fill to carry the last report date forward
        last_report_date = report_dates.ffill()

        # Step 3: forward-fill the raw values
        daily_ffill = daily.ffill()

        # Step 4: compute days since last observation (vectorised)
        days_elapsed = (
            pd.Series(full_date_range, index=full_date_range) - last_report_date
        ).dt.days.astype(float)

        # Step 5: apply exponential decay: value * exp(-lambda * days_elapsed)
        decay_factor = np.exp(-decay_lambda * days_elapsed)
        decayed = daily_ffill * decay_factor

        result_cols[f'exports_{category}_yoy_decay'] = decayed

    if result_cols:
        return pd.DataFrame(result_cols, index=full_date_range)
    return pd.DataFrame(index=full_date_range)


def zscore_features(df: pd.DataFrame, window_min: int = 252) -> pd.DataFrame:
    """Z-score features using expanding window up to t-1."""
    result = pd.DataFrame(index=df.index)

    # Determine actual min_periods based on available data
    max_per_symbol = df.groupby(level='symbol').size().max()
    effective_window_min = min(window_min, max(20, max_per_symbol // 2))

    if effective_window_min < window_min:
        # Not enough data for desired window, use what we have
        effective_window_min = max(20, effective_window_min)

    for col in df.columns:
        if df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
            # Expanding window z-score
            expanding = df.groupby(level='symbol')[col].expanding(min_periods=effective_window_min)
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
    
    # Beta and idiosyncratic volatility — properly computed
    beta = compute_beta(df_prices, df_benchmark, window=252)
    features_list.append(beta)
    idio_vol = compute_idiosyncratic_vol(df_prices, beta, df_benchmark, window=60)
    features_list.append(idio_vol)
    
    # Turnover
    features_list.append(compute_turnover(df_prices, window=20))
    
    # Combine all features
    features_df = pd.concat(features_list, axis=1)

    # ------------------------------------------------------------------
    # Broadcast scalar (date-level) features to all symbols using
    # vectorised reindex on the date level of the MultiIndex.
    # Pattern: map each row's date → scalar value in one pass, avoiding
    # any Python-level date iteration.
    # ------------------------------------------------------------------
    row_dates: pd.Index = features_df.index.get_level_values('as_of_date')
    dates: pd.Index = row_dates.unique()

    def _broadcast(scalar_df: pd.DataFrame) -> None:
        """Assign each column of scalar_df to features_df via date reindex."""
        for col in scalar_df.columns:
            features_df[col] = scalar_df[col].reindex(row_dates).values

    # FX features
    _broadcast(compute_fx_features(df_fx))

    # Memory features
    _broadcast(compute_memory_features(df_memory))

    # SOX features
    _broadcast(compute_sox_features(df_sox))

    # Flow features (already MultiIndex — use join)
    flow_feats = compute_flow_features(df_flows, df_prices)
    features_df = features_df.join(flow_feats, how='left')

    # Export features with decay (date-level → broadcast)
    export_feats = expand_exports_with_decay(
        df_exports,
        pd.DatetimeIndex(dates),
        half_life_days=exports_decay_half_life,
    )
    _broadcast(export_feats)
    
    # Z-score all features
    features_df = zscore_features(features_df, window_min=zscore_window_min)
    
    # Update global feature list
    global FEATURE_COLUMNS
    FEATURE_COLUMNS = [c for c in features_df.columns if not c.endswith('_missing')]
    
    return features_df
