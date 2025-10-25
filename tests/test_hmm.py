"""Tests for HMM regime model."""
import numpy as np
import pytest

from modeling.hmm import CycleHMM


def test_hmm_fit_transform():
    """Test HMM fitting and transformation."""
    # Generate synthetic data with 3 regimes
    np.random.seed(42)
    n_samples = 200
    n_features = 3
    
    X = np.random.randn(n_samples, n_features)
    
    hmm = CycleHMM(n_states=3, cov_type="full")
    hmm.fit(X)
    
    assert hmm.fitted
    
    # Transform should return state probabilities
    probs = hmm.transform(X)
    
    assert probs.shape == (n_samples, 3)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-6)  # Probabilities sum to 1
    assert (probs >= 0).all() and (probs <= 1).all()  # Valid probabilities


def test_hmm_predict():
    """Test HMM state prediction."""
    np.random.seed(42)
    X = np.random.randn(100, 3)
    
    hmm = CycleHMM(n_states=3)
    hmm.fit(X)
    
    states = hmm.predict(X)
    
    assert states.shape == (100,)
    assert set(states) <= {0, 1, 2}  # Only valid states


def test_hmm_handles_nan():
    """Test HMM handling of NaN values."""
    X = np.random.randn(100, 3)
    X[10:20, 1] = np.nan  # Inject some NaN
    
    hmm = CycleHMM(n_states=3)
    hmm.fit(X)  # Should fit on clean data
    
    probs = hmm.transform(X)
    
    # NaN rows should have NaN probabilities
    assert np.isnan(probs[10:20]).all()
    assert not np.isnan(probs[:10]).any()


def test_hmm_insufficient_data():
    """Test HMM with insufficient data."""
    X = np.random.randn(10, 3)  # Too few samples
    
    hmm = CycleHMM(n_states=3)
    
    with pytest.raises(ValueError, match="Insufficient"):
        hmm.fit(X)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
