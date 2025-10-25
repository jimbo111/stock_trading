"""Prediction store for caching model outputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from utils.logging import get_logger

logger = get_logger(__name__)


class PredictionStore:
    """Prediction store with parquet and JSON caching for API.
    
    Storage layout:
        root/
            dt=2025-01-01/predictions.parquet
            dt=2025-01-01/predictions.json
            ...
    """
    
    def __init__(self, root: str | Path):
        """Initialize prediction store.
        
        Args:
            root: Root directory for prediction storage
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
    
    def write(self, df: pd.DataFrame, date: str, model_version: str = "v1") -> None:
        """Write predictions for a specific date.
        
        Args:
            df: Prediction DataFrame with columns [p_up, state_prob_*, vol20_ann, ...]
            date: Date string (YYYY-MM-DD)
            model_version: Model version identifier
        """
        partition_dir = self.root / f"dt={date}"
        partition_dir.mkdir(exist_ok=True)
        
        # Write parquet
        parquet_path = partition_dir / "predictions.parquet"
        df.to_parquet(parquet_path, index=True)
        
        # Write JSON for API
        records = []
        for idx, row in df.iterrows():
            if isinstance(idx, tuple):
                as_of_date, symbol = idx
            else:
                as_of_date = date
                symbol = idx
            
            record = {
                "symbol": symbol,
                "as_of_date": str(as_of_date),
                "p_up": float(row['p_up']) if 'p_up' in row else None,
                "model_version": model_version,
                "degraded": False
            }
            
            # Add state probabilities
            state_probs = []
            for col in row.index:
                if col.startswith('state_prob_'):
                    state_probs.append(float(row[col]))
            if state_probs:
                record["state_probs"] = state_probs
            
            # Add optional fields
            if 'er20_hat_bps' in row:
                record["er20_hat_bps"] = float(row['er20_hat_bps'])
            if 'vol20_ann' in row:
                record["vol20_ann"] = float(row['vol20_ann'])
            if 'weight_suggested' in row:
                record["weight_suggested"] = float(row['weight_suggested'])
            
            records.append(record)
        
        json_path = partition_dir / "predictions.json"
        with open(json_path, 'w') as f:
            json.dump(records, f, indent=2)
        
        logger.info(f"Wrote {len(df)} predictions to {partition_dir}")
    
    def read(self, date: str) -> pd.DataFrame:
        """Read predictions for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Prediction DataFrame
        """
        partition_dir = self.root / f"dt={date}"
        parquet_path = partition_dir / "predictions.parquet"
        
        if not parquet_path.exists():
            raise FileNotFoundError(f"No predictions found for date {date}")
        
        return pd.read_parquet(parquet_path)
    
    def read_json(self, date: str) -> List[Dict]:
        """Read predictions as JSON for API.
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            List of prediction records
        """
        partition_dir = self.root / f"dt={date}"
        json_path = partition_dir / "predictions.json"
        
        if not json_path.exists():
            raise FileNotFoundError(f"No predictions found for date {date}")
        
        with open(json_path) as f:
            return json.load(f)
    
    def latest(self) -> pd.DataFrame:
        """Read predictions from the latest available partition.
        
        Returns:
            Prediction DataFrame from most recent date
        """
        partitions = sorted(self.root.glob("dt=*"))
        
        if not partitions:
            raise FileNotFoundError(f"No prediction partitions found in {self.root}")
        
        latest_partition = partitions[-1]
        date = latest_partition.name.replace("dt=", "")
        
        logger.info(f"Reading latest predictions from {date}")
        return self.read(date)
    
    def latest_json(self) -> List[Dict]:
        """Read latest predictions as JSON.
        
        Returns:
            List of prediction records from most recent date
        """
        partitions = sorted(self.root.glob("dt=*"))
        
        if not partitions:
            raise FileNotFoundError(f"No prediction partitions found in {self.root}")
        
        latest_partition = partitions[-1]
        date = latest_partition.name.replace("dt=", "")
        
        return self.read_json(date)
    
    def list_dates(self) -> list[str]:
        """List all available dates.
        
        Returns:
            Sorted list of date strings
        """
        partitions = sorted(self.root.glob("dt=*"))
        return [p.name.replace("dt=", "") for p in partitions]
