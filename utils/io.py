"""I/O utilities with schema validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def read_csv_with_schema(
    path: str | Path,
    schema_path: str | Path | None = None,
    **kwargs
) -> pd.DataFrame:
    """Read CSV with optional schema validation.

    Args:
        path: Path to CSV file
        schema_path: Optional path to JSON schema file
        **kwargs: Additional arguments passed to pd.read_csv

    Returns:
        DataFrame

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If schema validation fails
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path, **kwargs)

    if schema_path is not None:
        validate_dataframe_schema(df, schema_path)

    return df


def validate_dataframe_schema(df: pd.DataFrame, schema_path: str | Path) -> None:
    """Validate DataFrame against JSON schema.

    Args:
        df: DataFrame to validate
        schema_path: Path to JSON schema file

    Raises:
        ValueError: If validation fails
    """
    schema_path = Path(schema_path)

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    # Basic validation - check required columns
    if "required_columns" in schema:
        missing = set(schema["required_columns"]) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    # Check data types if specified
    if "dtypes" in schema:
        for col, expected_type in schema["dtypes"].items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if not _dtype_matches(actual_type, expected_type):
                    raise ValueError(
                        f"Column {col} has dtype {actual_type}, "
                        f"expected {expected_type}"
                    )


def _dtype_matches(actual: str, expected: str) -> bool:
    """Check if actual dtype matches expected.

    Args:
        actual: Actual dtype string
        expected: Expected dtype pattern

    Returns:
        True if match
    """
    # Exact match
    if actual == expected:
        return True

    # Flexible matching
    if expected == "numeric" and actual in ["int64", "float64", "int32", "float32"]:
        return True

    if expected == "datetime" and "datetime" in actual:
        return True

    if expected == "object" and actual == "object":
        return True

    return False


def read_parquet_partitioned(
    root: str | Path,
    partition: str | None = None
) -> pd.DataFrame:
    """Read parquet files from partitioned directory.

    Args:
        root: Root directory
        partition: Optional partition (e.g., 'dt=2025-01-01')

    Returns:
        DataFrame
    """
    root = Path(root)

    if partition:
        path = root / partition
        if not path.exists():
            raise FileNotFoundError(f"Partition not found: {path}")
        return pd.read_parquet(path)
    else:
        # Read all partitions
        return pd.read_parquet(root)


def write_json(data: Dict[str, Any], path: str | Path) -> None:
    """Write data to JSON file.

    Args:
        data: Dictionary to write
        path: Output path
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def read_json(path: str | Path) -> Dict[str, Any]:
    """Read JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON as dictionary
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path) as f:
        return json.load(f)
