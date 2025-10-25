"""Model training and scoring pipeline."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modeling.classifier_enet import EnetClassifier
from modeling.hmm import CycleHMM
from stores.feature_store import FeatureStore
from stores.label_store import LabelStore
from stores.prediction_store import PredictionStore
from utils.cv import PurgedKFold
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@dataclass
class TrainArtifacts:
    """Container for trained model artifacts."""
    hmm: CycleHMM
    clf: EnetClassifier
    feature_columns: list[str]
    hmm_feature_columns: list[str]


def select_hmm_features(df_feat: pd.DataFrame) -> list[str]:
    """Select features for HMM regime detection.
    
    Typically use returns, volatility, and momentum indicators.
    """
    candidates = [
        'ret_1d', 'ret_5d', 'ret_20d',
        'rv_20d', 'mom_1m', 'mom_3m',
        'sox_chg_5d', 'sox_chg_20d'
    ]
    
    return [c for c in candidates if c in df_feat.columns]


def fit_pipeline(
    df_feat: pd.DataFrame,
    df_labels: pd.DataFrame,
    config: dict
) -> TrainArtifacts:
    """Fit complete pipeline: HMM + calibrated classifier.
    
    Args:
        df_feat: Feature DataFrame with MultiIndex [as_of_date, symbol]
        df_labels: Label DataFrame with MultiIndex [as_of_date, symbol]
        config: Project configuration dict
        
    Returns:
        TrainArtifacts containing fitted models
    """
    logger.info("Starting pipeline training")
    
    # Merge features and labels
    df = df_feat.join(df_labels, how='inner')
    df = df.dropna(subset=['y_class'])
    
    logger.info(f"Training on {len(df)} samples")
    
    # Select HMM features
    hmm_features = select_hmm_features(df_feat)
    logger.info(f"HMM features: {hmm_features}")
    
    # Prepare HMM input
    Z = df[hmm_features].values
    
    # Fit HMM
    logger.info("Fitting HMM for regime detection")
    hmm = CycleHMM(
        n_states=config['hmm']['n_states'],
        cov_type=config['hmm']['cov_type']
    )
    hmm.fit(Z)
    
    # Get state probabilities
    state_probs = hmm.transform(Z)
    
    # Add state probabilities as features
    for i in range(config['hmm']['n_states']):
        df[f'state_prob_{i}'] = state_probs[:, i]
    
    # Prepare classifier features (original + state probs)
    feature_cols = [c for c in df_feat.columns if not c.endswith('_missing')]
    feature_cols += [f'state_prob_{i}' for i in range(config['hmm']['n_states'])]
    
    X = df[feature_cols].values
    y = df['y_class'].values
    
    # Purged K-Fold cross-validation for OOF scores
    logger.info("Performing purged K-Fold CV for calibration")
    cv = PurgedKFold(
        n_splits=5,
        horizon=config['horizon_days'],
        embargo=config['embargo_days']
    )
    
    oof_scores = np.full(len(df), np.nan)
    oof_y = y.copy()
    
    for fold, (train_idx, val_idx) in enumerate(cv.split(df)):
        logger.info(f"Fold {fold + 1}/5: train={len(train_idx)}, val={len(val_idx)}")
        
        X_train, X_val = X[train_idx], X[val_idx]
        y_train = y[train_idx]
        
        # Fit fold classifier
        fold_clf = EnetClassifier(C=1.0, l1_ratio=0.3)
        fold_clf.fit(X_train, y_train)
        
        # Predict on validation
        oof_scores[val_idx] = fold_clf.predict_proba(X_val)
    
    # Fit final classifier with calibration
    logger.info("Fitting final classifier with isotonic calibration")
    clf = EnetClassifier(C=1.0, l1_ratio=0.3)
    clf.fit(X, y, oof_scores=oof_scores, oof_y=oof_y)
    
    # Log feature importance
    importance = clf.get_feature_importance()
    top_features = sorted(zip(feature_cols, importance), key=lambda x: x[1], reverse=True)[:10]
    logger.info("Top 10 features:")
    for feat, imp in top_features:
        logger.info(f"  {feat}: {imp:.4f}")
    
    return TrainArtifacts(
        hmm=hmm,
        clf=clf,
        feature_columns=feature_cols,
        hmm_feature_columns=hmm_features
    )


def score_pipeline(
    art: TrainArtifacts,
    df_feat_today: pd.DataFrame
) -> pd.DataFrame:
    """Score today's features with trained pipeline.
    
    Args:
        art: Trained model artifacts
        df_feat_today: Today's features (MultiIndex [as_of_date, symbol])
        
    Returns:
        DataFrame with predictions: [p_up, state_prob_*, ...]
    """
    logger.info("Scoring pipeline")
    
    # Get HMM state probabilities
    Z = df_feat_today[art.hmm_feature_columns].values
    state_probs = art.hmm.transform(Z)
    
    # Add state probs to features
    df_with_states = df_feat_today.copy()
    for i in range(state_probs.shape[1]):
        df_with_states[f'state_prob_{i}'] = state_probs[:, i]
    
    # Prepare classifier input
    X = df_with_states[art.feature_columns].values
    
    # Predict
    p_up = art.clf.predict_proba(X)
    
    # Build results DataFrame
    results = pd.DataFrame({
        'p_up': p_up
    }, index=df_feat_today.index)
    
    # Add state probabilities
    for i in range(state_probs.shape[1]):
        results[f'state_prob_{i}'] = state_probs[:, i]
    
    # Add volatility for position sizing
    if 'rv_20d' in df_feat_today.columns:
        results['vol20_ann'] = df_feat_today['rv_20d']
    
    logger.info(f"Generated predictions for {len(results)} symbols")
    
    return results


def load_config():
    """Load project configuration."""
    config_path = Path("config/default.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    """Main training/scoring entrypoint."""
    parser = argparse.ArgumentParser(description="Model pipeline")
    parser.add_argument("--train", action="store_true", help="Train models")
    parser.add_argument("--score", action="store_true", help="Score latest features")
    parser.add_argument("--use-samples", action="store_true", help="Use sample data")
    
    args = parser.parse_args()
    
    if not (args.train or args.score):
        logger.error("Must specify --train or --score")
        return
    
    config = load_config()
    
    # Load features and labels
    feat_store = FeatureStore(config['paths']['gold'])
    label_store = LabelStore(config['paths']['gold'])
    
    df_feat = feat_store.latest()
    
    if args.train:
        logger.info("Training mode")
        df_labels = label_store.latest()
        
        artifacts = fit_pipeline(df_feat, df_labels, config)
        
        # TODO: Save artifacts (pickle, mlflow, etc.)
        logger.info("Training complete")
    
    if args.score:
        logger.info("Scoring mode")
        # TODO: Load artifacts from storage
        logger.error("Scoring requires saved artifacts - not implemented")


if __name__ == "__main__":
    main()
