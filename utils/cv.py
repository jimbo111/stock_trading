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
        embargo: int = 20,
        min_train_periods: int = 50,
    ):
        """Initialize purged walk-forward expanding-window CV.

        Args:
            n_splits: Number of folds.  The time axis is divided into
                ``n_splits + 1`` equal blocks.  Fold ``i`` trains on
                blocks ``0..i`` and validates on block ``i+1``, giving
                ``n_splits`` folds in total.
            horizon: Forward-looking label horizon in days.  Used for
                the purge cutoff so that training observations whose
                forward window overlaps the validation period are removed.
            embargo: Additional gap in days appended after the purge
                period before the validation window begins.
            min_train_periods: Minimum number of training observations
                required to emit a fold.  Folds below this threshold are
                silently skipped.
        """
        self.n_splits = n_splits
        self.horizon = horizon
        self.embargo = embargo
        self.min_train_periods = min_train_periods

    def split(
        self,
        df: pd.DataFrame
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Generate walk-forward expanding-window train/validation splits.

        The time axis is divided into ``n_splits + 1`` equal-sized blocks.
        For fold ``i`` (0-indexed):
        - Training set: all observations whose date falls within blocks
          ``0`` through ``i``, minus the purge/embargo tail.
        - Validation set: all observations whose date falls within block
          ``i + 1``.

        This guarantees that:
        1. Training always uses strictly past data relative to validation.
        2. The training window expands monotonically across folds.
        3. No forward-looking leakage via the label horizon.

        Args:
            df: DataFrame with a DatetimeIndex or a MultiIndex whose
                first level is named ``as_of_date``.

        Yields:
            Tuple of (train_indices, val_indices) as integer position
            arrays suitable for iloc-style indexing.
        """
        # ------------------------------------------------------------------
        # 1. Extract the date axis
        # ------------------------------------------------------------------
        if isinstance(df.index, pd.MultiIndex):
            dates = df.index.get_level_values('as_of_date')
        else:
            dates = df.index

        unique_dates = sorted(dates.unique())
        n_dates = len(unique_dates)

        # ------------------------------------------------------------------
        # 2. Divide into (n_splits + 1) blocks
        #    Block boundaries are stored as indices into unique_dates.
        # ------------------------------------------------------------------
        n_blocks = self.n_splits + 1
        # Use np.array_split indices to get as-equal-as-possible blocks
        block_boundaries: list[tuple[int, int]] = []
        indices = np.array_split(np.arange(n_dates), n_blocks)
        for block in indices:
            if len(block) == 0:
                continue
            block_boundaries.append((int(block[0]), int(block[-1])))

        if len(block_boundaries) < 2:
            # Not enough data to form even one fold
            return

        # ------------------------------------------------------------------
        # 3. Walk-forward: fold i trains on blocks 0..i, validates on i+1
        # ------------------------------------------------------------------
        for fold in range(len(block_boundaries) - 1):
            # Validation window
            val_block_start_idx, val_block_end_idx = block_boundaries[fold + 1]
            val_start_date = unique_dates[val_block_start_idx]
            val_end_date = unique_dates[val_block_end_idx]

            # Training window: all blocks up to and including fold `fold`
            train_raw_end_idx = block_boundaries[fold][1]
            train_raw_end_date = unique_dates[train_raw_end_idx]

            # Purge: remove training obs whose label window touches validation.
            # A label computed at date t covers [t, t+horizon].  We must
            # exclude any t where t + horizon >= val_start_date, i.e.
            # t >= val_start_date - horizon.  We also add the embargo gap.
            purge_cutoff_date = val_start_date - pd.Timedelta(
                days=self.horizon + self.embargo
            )

            # Training mask: past data only, purged tail removed
            train_mask = (dates <= train_raw_end_date) & (dates <= purge_cutoff_date)
            # Validation mask: exactly the validation block
            val_mask = (dates >= val_start_date) & (dates <= val_end_date)

            train_indices = np.where(train_mask)[0]
            val_indices = np.where(val_mask)[0]

            # Skip fold if either set is too small
            if len(train_indices) < self.min_train_periods or len(val_indices) < 1:
                import logging
                logging.getLogger(__name__).warning(
                    f"Skipping fold {fold}: train={len(train_indices)} "
                    f"(min={self.min_train_periods}), val={len(val_indices)}"
                )
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
    embargo: int = 20,
    min_train_periods: int = 50,
) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
    """Convenience function for purged walk-forward expanding-window splits.

    Args:
        df: DataFrame with temporal index (DatetimeIndex or MultiIndex
            with ``as_of_date`` level).
        n_splits: Number of folds.
        horizon: Forward horizon in days used for purge calculation.
        embargo: Additional embargo in days beyond the purge period.
        min_train_periods: Minimum training observations required to
            emit a fold.

    Yields:
        (train_indices, val_indices) integer position arrays for each fold.
    """
    cv = PurgedKFold(
        n_splits=n_splits,
        horizon=horizon,
        embargo=embargo,
        min_train_periods=min_train_periods,
    )
    yield from cv.split(df)
