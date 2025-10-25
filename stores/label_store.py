"""Label store for parquet-based label storage."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.logging import get_logger

logger = get_logger(__name__)


class LabelStore:
    """Parquet-based label store with date partitioning.
    
    Storage layout:
        root/
            dt=2025-01-01/labels.parquet
            dt=2025-01-02/labels.parquet
            ...
    """
    
    def __init__(self, root: str | Path):
        """Initialize label store.
        
        Args:
            root: Root directory for label storage
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
    
    def write(self, df: pd.DataFrame, date: str) -> None:
        """Write labels for a specific date.
        
        Args:
            df: Label DataFrame (should have MultiIndex [as_of_date, symbol])
            date: Date string (YYYY-MM-DD)
        """
        partition_dir = self.root / f"dt={date}"
        partition_dir.mkdir(exist_ok=True)
        
        output_path = partition_dir / "labels.parquet"
        df.to_parquet(output_path, index=True)
        
        logger.info(f"Wrote {len(df)} label rows to {output_path}")
    
    def read(self, date: str) -> pd.DataFrame:
        """Read labels for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Label DataFrame
        """
        partition_dir = self.root / f"dt={date}"
        input_path = partition_dir / "labels.parquet"
        
        if not input_path.exists():
            raise FileNotFoundError(f"No labels found for date {date}")
        
        df = pd.read_parquet(input_path)
        logger.info(f"Read {len(df)} label rows from {input_path}")
        
        return df
    
    def latest(self) -> pd.DataFrame:
        """Read labels from the latest available partition.
        
        Returns:
            Label DataFrame from most recent date
        """
        partitions = sorted(self.root.glob("dt=*"))
        
        if not partitions:
            raise FileNotFoundError(f"No label partitions found in {self.root}")
        
        latest_partition = partitions[-1]
        date = latest_partition.name.replace("dt=", "")
        
        logger.info(f"Reading latest labels from {date}")
        return self.read(date)
    
    def list_dates(self) -> list[str]:
        """List all available dates.
        
        Returns:
            Sorted list of date strings
        """
        partitions = sorted(self.root.glob("dt=*"))
        return [p.name.replace("dt=", "") for p in partitions]
