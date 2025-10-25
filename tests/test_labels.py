"""Tests for label generation."""
import numpy as np
import pandas as pd
import pytest

from labeling.make_labels import make_excess_return_labels


def test_make_excess_return_labels_basic():
    """Test basic label generation."""
    # Create simple test data
    dates = pd.date_range('2025-01-01', periods=50, freq='D')
    
    data = []
    for date in dates:
        data.append({'as_of_date': date, 'symbol': '005930.KS', 'close': 100 * (1 + np.random.randn() * 0.01)})
        data.append({'as_of_date': date, 'symbol': '^KS11', 'close': 2500 * (1 + np.random.randn() * 0.01)})
    
    df = pd.DataFrame(data)
    
    labels = make_excess_return_labels(df, horizon_days=20)
    
    assert 'er20' in labels.columns
    assert 'y_class' in labels.columns
    assert len(labels) > 0
    assert labels['y_class'].isin([0, 1]).all()


def test_excess_return_calculation():
    """Test that excess returns are calculated correctly."""
    dates = pd.date_range('2025-01-01', periods=30, freq='D')
    
    # Create deterministic data
    data = []
    for i, date in enumerate(dates):
        # Stock gains 10%
        data.append({'as_of_date': date, 'symbol': 'TEST.KS', 'close': 100 * (1.1 ** (i / 29))})
        # Benchmark gains 5%
        data.append({'as_of_date': date, 'symbol': '^KS11', 'close': 1000 * (1.05 ** (i / 29))})
    
    df = pd.DataFrame(data)
    
    labels = make_excess_return_labels(df, horizon_days=20)
    
    # Excess return should be positive (stock outperforms benchmark)
    assert labels['er20'].mean() > 0
    assert labels['y_class'].mean() > 0.5


def test_missing_benchmark():
    """Test handling of missing benchmark."""
    dates = pd.date_range('2025-01-01', periods=30, freq='D')
    
    data = []
    for date in dates:
        data.append({'as_of_date': date, 'symbol': '005930.KS', 'close': 100})
    
    df = pd.DataFrame(data)
    
    # Should handle missing benchmark gracefully
    labels = make_excess_return_labels(df, horizon_days=20)
    
    assert len(labels) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
