"""Hidden Markov Model for regime detection."""
from __future__ import annotations

import numpy as np
from hmmlearn import hmm


class CycleHMM:
    """Gaussian Hidden Markov Model for market regime detection.

    Wraps hmmlearn.hmm.GaussianHMM with additional utilities for
    handling NaN values and regime classification.

    Fitting uses multiple random restarts to avoid local minima, and
    standardizes features before training so that Gaussian emissions
    operate on comparable scales.
    """

    def __init__(
        self,
        n_states: int = 3,
        cov_type: str = "full",
        n_iter: int = 100,
        random_state: int = 42,
        n_restarts: int = 10
    ):
        """Initialize HMM.

        Args:
            n_states: Number of hidden states (regimes)
            cov_type: Covariance type ('full', 'diag', 'spherical', 'tied')
            n_iter: Maximum number of EM iterations
            random_state: Base random seed; each restart uses seed + restart_index
            n_restarts: Number of random restarts; best log-likelihood wins
        """
        self.n_states = n_states
        self.cov_type = cov_type
        self.n_iter = n_iter
        self.random_state = random_state
        self.n_restarts = n_restarts

        # Instantiate a placeholder; replaced in fit() by the best restart
        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type=cov_type,
            n_iter=n_iter,
            random_state=random_state
        )

        # Feature scaler parameters — set in fit(), applied in transform/predict
        self._scaler_mean: np.ndarray | None = None
        self._scaler_scale: np.ndarray | None = None

        self.fitted = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scale(self, X: np.ndarray) -> np.ndarray:
        """Apply stored zero-mean / unit-variance scaling.

        Args:
            X: Raw feature matrix (n_samples, n_features)

        Returns:
            Standardized feature matrix
        """
        return (X - self._scaler_mean) / self._scaler_scale

    def fit(self, X: np.ndarray) -> "CycleHMM":
        """Fit HMM to data using multiple random restarts.

        Features are standardized (zero mean, unit variance) before
        fitting so that HMM Gaussian emissions are on comparable scales.
        The scaler parameters are stored for use in transform() and
        predict().  Among all restarts the model with the highest
        log-likelihood on the clean training data is kept.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            self

        Raises:
            ValueError: If insufficient valid (non-NaN) samples
        """
        # Remove NaN rows
        valid_mask = ~np.isnan(X).any(axis=1)
        X_clean = X[valid_mask]

        if len(X_clean) < 50:
            raise ValueError(
                f"Insufficient data for HMM fitting: {len(X_clean)} valid samples "
                f"(minimum 50 required)"
            )

        # Fit and store the scaler from training data
        self._scaler_mean = X_clean.mean(axis=0)
        self._scaler_scale = X_clean.std(axis=0)
        # Guard against zero-variance features (e.g. constant columns)
        self._scaler_scale = np.where(
            self._scaler_scale == 0, 1.0, self._scaler_scale
        )

        X_scaled = self._scale(X_clean)

        # Multi-restart: try n_restarts seeds, keep best log-likelihood
        best_model: hmm.GaussianHMM | None = None
        best_score = -np.inf

        for i in range(self.n_restarts):
            seed = self.random_state + i
            candidate = hmm.GaussianHMM(
                n_components=self.n_states,
                covariance_type=self.cov_type,
                n_iter=self.n_iter,
                random_state=seed
            )
            try:
                candidate.fit(X_scaled)
                score = candidate.score(X_scaled)
            except Exception:
                # Degenerate covariance or numerical error — skip this seed
                continue

            if score > best_score:
                best_score = score
                best_model = candidate

        if best_model is None:
            raise ValueError(
                "All HMM restarts failed to converge. "
                "Try increasing n_iter or reducing n_states."
            )

        self.model = best_model
        self.fitted = True

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Get state probabilities for each sample.

        Args:
            X: Feature matrix (n_samples, n_features) in raw (unscaled) space

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

            # Apply the same scaling used during fit
            X_scaled = self._scale(X_clean)

            # Get posterior probabilities
            probs_clean = self.model.predict_proba(X_scaled)

            # Fill valid rows
            probs[valid_mask] = probs_clean

        return probs

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict most likely state for each sample.

        Args:
            X: Feature matrix (n_samples, n_features) in raw (unscaled) space

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

            # Apply the same scaling used during fit
            X_scaled = self._scale(X_clean)

            # Predict states
            states_clean = self.model.predict(X_scaled)

            # Fill valid rows
            states[valid_mask] = states_clean

        return states

    def score(self, X: np.ndarray) -> float:
        """Compute log-likelihood of data.

        Args:
            X: Feature matrix (n_samples, n_features) in raw (unscaled) space

        Returns:
            Log-likelihood
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before score")

        # Remove NaN rows and apply scaling
        valid_mask = ~np.isnan(X).any(axis=1)
        X_clean = X[valid_mask]
        X_scaled = self._scale(X_clean)

        return self.model.score(X_scaled)

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
