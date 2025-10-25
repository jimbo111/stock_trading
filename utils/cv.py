"""Purged K-Fold cross-validation for time series.

Implements purged and embargoed cross-validation to prevent label leakage
in time series forecasting tasks.
"""
from __future__ import annotations

from typing import Generator, Tuple

import numpy as np
import pandas as pd


class PurgedKFold:
    """Purged K-Fold cross-validation for time series.

    Prevents label leakage by:
    1. Purging: Removing samples within `horizon` days after training set
    2. Embargo: Adding additional gap of `embargo` days after purge period

    This ensures that validation samples don't contain information that
    would have been available during the training period.
    """

    def __init__(
        self,
        n_splits: int = 5,
        horizon: int = 20,
        embargo: int = 20
    ):
        """Initialize purged k-fold.

        Args:
            n_splits: Number of folds
            horizon: Forward-looking horizon in days (label period)
            embargo: Additional embargo period in days
        """
        self.n_splits = n_splits
        self.horizon = horizon
        self.embargo = embargo

    def split(
        self,
        df: pd.DataFrame
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Generate train/validation splits.

        Args:
            df: DataFrame with DatetimeIndex or MultiIndex with as_of_date level

        Yields:
            (train_indices, val_indices) for each fold
        """
        # Extract dates from index
        if isinstance(df.index, pd.MultiIndex):
            dates = df.index.get_level_values('as_of_date')
        else:
            dates = df.index

        unique_dates = sorted(dates.unique())
        n_dates = len(unique_dates)

        # Calculate fold size
        fold_size = n_dates // self.n_splits

        for fold in range(self.n_splits):
            # Validation period for this fold
            val_start_idx = fold * fold_size
            val_end_idx = min((fold + 1) * fold_size, n_dates)

            if val_start_idx >= n_dates:
                break

            val_start_date = unique_dates[val_start_idx]
            val_end_date = unique_dates[val_end_idx - 1]

            # Training period: everything before validation
            train_end_date = unique_dates[max(0, val_start_idx - 1)]

            # Apply purge and embargo to training set
            # Remove samples within (horizon + embargo) days before validation
            purge_cutoff_date = val_start_date - pd.Timedelta(
                days=self.horizon + self.embargo
            )

            # Get indices
            train_mask = dates <= purge_cutoff_date
            val_mask = (dates >= val_start_date) & (dates <= val_end_date)

            train_indices = np.where(train_mask)[0]
            val_indices = np.where(val_mask)[0]

            # Skip fold if insufficient data
            if len(train_indices) < 50 or len(val_indices) < 10:
                continue

            yield train_indices, val_indices

    def get_n_splits(self) -> int:
        """Get number of splits.

        Returns:
            Number of folds
        """
        return self.n_splits


def purged_cv_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
    horizon: int = 20,
    embargo: int = 20
) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
    """Convenience function for purged k-fold splits.

    Args:
        df: DataFrame with temporal index
        n_splits: Number of folds
        horizon: Forward horizon in days
        embargo: Additional embargo in days

    Yields:
        (train_indices, val_indices) for each fold
    """
    cv = PurgedKFold(n_splits=n_splits, horizon=horizon, embargo=embargo)
    yield from cv.split(df)
