"""Feature store for parquet-based feature storage."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.logging import get_logger

logger = get_logger(__name__)


class FeatureStore:
    """Parquet-based feature store with date partitioning.

    Storage layout:
        root/
            dt=2025-01-01/features.parquet
            dt=2025-01-02/features.parquet
            ...
    """

    def __init__(self, root: str | Path):
        """Initialize feature store.

        Args:
            root: Root directory for feature storage
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, df: pd.DataFrame, date: str) -> None:
        """Write features for a specific date.

        Args:
            df: Feature DataFrame (should have MultiIndex [as_of_date, symbol])
            date: Date string (YYYY-MM-DD)
        """
        partition_dir = self.root / f"dt={date}"
        partition_dir.mkdir(exist_ok=True)

        output_path = partition_dir / "features.parquet"
        df.to_parquet(output_path, index=True)

        logger.info(f"Wrote {len(df)} feature rows to {output_path}")

    def read(self, date: str) -> pd.DataFrame:
        """Read features for a specific date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Feature DataFrame
        """
        partition_dir = self.root / f"dt={date}"
        input_path = partition_dir / "features.parquet"

        if not input_path.exists():
            raise FileNotFoundError(f"No features found for date {date}")

        df = pd.read_parquet(input_path)
        logger.info(f"Read {len(df)} feature rows from {input_path}")

        return df

    def latest(self) -> pd.DataFrame:
        """Read features from the latest available partition.

        Returns:
            Feature DataFrame from most recent date
        """
        partitions = sorted(self.root.glob("dt=*"))

        if not partitions:
            raise FileNotFoundError(f"No feature partitions found in {self.root}")

        latest_partition = partitions[-1]
        date = latest_partition.name.replace("dt=", "")

        logger.info(f"Reading latest features from {date}")
        return self.read(date)

    def list_dates(self) -> list[str]:
        """List all available dates with features.

        Returns:
            Sorted list of date strings that have features.parquet
        """
        partitions = sorted(self.root.glob("dt=*"))
        # Only return dates that actually have features.parquet
        valid_dates = []
        for p in partitions:
            if (p / "features.parquet").exists():
                valid_dates.append(p.name.replace("dt=", ""))
        return valid_dates

    def read_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Read features for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Concatenated feature DataFrame
        """
        dates = self.list_dates()
        selected_dates = [d for d in dates if start_date <= d <= end_date]

        if not selected_dates:
            raise FileNotFoundError(
                f"No features found between {start_date} and {end_date}"
            )

        dfs = [self.read(date) for date in selected_dates]
        result = pd.concat(dfs, axis=0)

        logger.info(
            f"Read {len(result)} feature rows from {len(selected_dates)} dates "
            f"({start_date} to {end_date})"
        )

        return result
