"""Elastic Net logistic classifier with isotonic calibration."""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler


class EnetClassifier:
    """Elastic Net logistic regression with optional calibration.
    
    Uses L1+L2 penalty for feature selection and regularization.
    Supports isotonic calibration on out-of-fold predictions.
    """
    
    def __init__(self, C: float = 1.0, l1_ratio: float = 0.3):
        """Initialize classifier.
        
        Args:
            C: Inverse of regularization strength (smaller = more regularization)
            l1_ratio: Mixing parameter between L1 and L2 (0=L2, 1=L1)
        """
        self.C = C
        self.l1_ratio = l1_ratio
        self.clf = LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            l1_ratio=l1_ratio,
            C=C,
            max_iter=5000,
            n_jobs=-1,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.cal = None
        self.fitted = False
    
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        oof_scores: np.ndarray | None = None,
        oof_y: np.ndarray | None = None
    ) -> "EnetClassifier":
        """Fit classifier and optionally calibrate.
        
        Args:
            X: Training features (n_samples, n_features)
            y: Training labels (n_samples,)
            oof_scores: Out-of-fold scores for calibration (optional)
            oof_y: Out-of-fold true labels for calibration (optional)
            
        Returns:
            Self for chaining
        """
        # Remove NaN rows
        mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X_clean = X[mask]
        y_clean = y[mask]

        if len(X_clean) == 0:
            raise ValueError("No valid samples after removing NaN")

        # Fit scaler on clean training data and standardize
        # L1/L2 regularization is scale-sensitive; without this, z-scored
        # features (std≈1) and HMM state probabilities (range 0-1) are
        # penalized disproportionately.
        X_scaled = self.scaler.fit_transform(X_clean)

        # Fit classifier
        self.clf.fit(X_scaled, y_clean)
        self.fitted = True
        
        # Fit calibrator if OOF data provided
        if oof_scores is not None and oof_y is not None:
            # Remove NaN from OOF data
            oof_mask = ~np.isnan(oof_scores) & ~np.isnan(oof_y)
            oof_scores_clean = oof_scores[oof_mask]
            oof_y_clean = oof_y[oof_mask]
            
            if len(oof_scores_clean) > 10:
                self.cal = IsotonicRegression(out_of_bounds="clip")
                self.cal.fit(oof_scores_clean, oof_y_clean)
        
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict calibrated probabilities.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            
        Returns:
            Probability of positive class (n_samples,)
        """
        if not self.fitted:
            raise ValueError("Classifier must be fitted before prediction")
        
        # Handle NaN rows
        mask = ~np.isnan(X).any(axis=1)
        probs = np.full(len(X), np.nan)

        if mask.sum() == 0:
            return probs

        # Apply the same scaling fitted during training
        X_scaled = self.scaler.transform(X[mask])

        # Get raw scores
        raw = self.clf.decision_function(X_scaled)
        
        # Apply calibration if available
        if self.cal is not None:
            probs[mask] = self.cal.transform(raw)
        else:
            # Fallback to logistic link
            probs[mask] = 1 / (1 + np.exp(-raw))
        
        return probs
    
    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict class labels.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            threshold: Probability threshold for positive class
            
        Returns:
            Predicted labels (n_samples,)
        """
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)
    
    def get_coefficients(self) -> np.ndarray:
        """Get feature coefficients."""
        if not self.fitted:
            raise ValueError("Classifier must be fitted")
        return self.clf.coef_[0]
    
    def get_feature_importance(self) -> np.ndarray:
        """Get absolute feature importance."""
        return np.abs(self.get_coefficients())
