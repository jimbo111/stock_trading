"""Hidden Markov Model for regime detection."""
from __future__ import annotations

import numpy as np
from hmmlearn import hmm


class CycleHMM:
    """Gaussian Hidden Markov Model for market regime detection.

    Wraps hmmlearn.hmm.GaussianHMM with additional utilities for
    handling NaN values and regime classification.
    """

    def __init__(
        self,
        n_states: int = 3,
        cov_type: str = "full",
        n_iter: int = 100,
        random_state: int = 42
    ):
        """Initialize HMM.

        Args:
            n_states: Number of hidden states (regimes)
            cov_type: Covariance type ('full', 'diag', 'spherical', 'tied')
            n_iter: Maximum number of EM iterations
            random_state: Random seed for reproducibility
        """
        self.n_states = n_states
        self.cov_type = cov_type
        self.n_iter = n_iter
        self.random_state = random_state

        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type=cov_type,
            n_iter=n_iter,
            random_state=random_state
        )

        self.fitted = False

    def fit(self, X: np.ndarray) -> CycleHMM:
        """Fit HMM to data.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            self

        Raises:
            ValueError: If insufficient data
        """
        # Remove NaN rows
        valid_mask = ~np.isnan(X).any(axis=1)
        X_clean = X[valid_mask]

        if len(X_clean) < 50:
            raise ValueError(
                f"Insufficient data for HMM fitting: {len(X_clean)} valid samples "
                f"(minimum 50 required)"
            )

        # Fit model
        self.model.fit(X_clean)
        self.fitted = True

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Get state probabilities for each sample.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            State probability matrix (n_samples, n_states)
            NaN rows in input will have NaN probabilities
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before transform")

        # Initialize output with NaN
        probs = np.full((len(X), self.n_states), np.nan)

        # Get valid rows (no NaN)
        valid_mask = ~np.isnan(X).any(axis=1)

        if valid_mask.sum() > 0:
            X_clean = X[valid_mask]

            # Get posterior probabilities
            probs_clean = self.model.predict_proba(X_clean)

            # Fill valid rows
            probs[valid_mask] = probs_clean

        return probs

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict most likely state for each sample.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            State predictions (n_samples,)
            NaN rows will have state -1
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before predict")

        # Initialize with -1 (invalid state)
        states = np.full(len(X), -1, dtype=int)

        # Get valid rows
        valid_mask = ~np.isnan(X).any(axis=1)

        if valid_mask.sum() > 0:
            X_clean = X[valid_mask]

            # Predict states
            states_clean = self.model.predict(X_clean)

            # Fill valid rows
            states[valid_mask] = states_clean

        return states

    def score(self, X: np.ndarray) -> float:
        """Compute log-likelihood of data.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Log-likelihood
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before score")

        # Remove NaN rows
        valid_mask = ~np.isnan(X).any(axis=1)
        X_clean = X[valid_mask]

        return self.model.score(X_clean)

    def get_params(self) -> dict:
        """Get model parameters.

        Returns:
            Dictionary with means, covariances, transition matrix
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before getting params")

        return {
            "means": self.model.means_,
            "covars": self.model.covars_,
            "transmat": self.model.transmat_,
            "startprob": self.model.startprob_
        }
