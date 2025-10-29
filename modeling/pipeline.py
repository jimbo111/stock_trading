"""Model training and scoring pipeline."""
from __future__ import annotations

import argparse
import pickle
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
    logger.info(f"HMM features (initial): {hmm_features}")

    # Filter to features with sufficient non-null values
    hmm_features_valid = []
    for feat in hmm_features:
        if feat in df.columns:
            non_null_count = df[feat].notna().sum()
            if non_null_count >= 50:  # At least 50 valid samples
                hmm_features_valid.append(feat)
            else:
                logger.warning(f"Excluding {feat} from HMM (only {non_null_count} non-null values)")

    if len(hmm_features_valid) < 3:
        raise ValueError(f"Insufficient HMM features with valid data: only {len(hmm_features_valid)} features available")

    hmm_features = hmm_features_valid
    logger.info(f"HMM features (filtered): {hmm_features}")

    # Prepare HMM input - drop rows with any NaN in HMM features
    Z_hmm = df[hmm_features].dropna()
    Z = Z_hmm.values
    logger.info(f"HMM input: {Z.shape[0]} samples with {Z.shape[1]} features")

    # Fit HMM
    logger.info("Fitting HMM for regime detection")
    hmm = CycleHMM(
        n_states=config['hmm']['n_states'],
        cov_type=config['hmm']['cov_type']
    )
    hmm.fit(Z)

    # Get state probabilities for the valid indices
    state_probs = hmm.transform(Z)

    # Initialize state probability columns with NaN
    for i in range(config['hmm']['n_states']):
        df[f'state_prob_{i}'] = np.nan

    # Assign state probabilities to the valid indices
    for i in range(config['hmm']['n_states']):
        df.loc[Z_hmm.index, f'state_prob_{i}'] = state_probs[:, i]
    
    # Prepare classifier features (original + state probs)
    feature_cols = [c for c in df_feat.columns if not c.endswith('_missing')]
    feature_cols += [f'state_prob_{i}' for i in range(config['hmm']['n_states'])]

    # Drop rows with missing state probabilities
    df_train = df.dropna(subset=[f'state_prob_{i}' for i in range(config['hmm']['n_states'])])
    logger.info(f"After filtering for valid HMM states: {len(df_train)} samples")

    if len(df_train) < 50:
        raise ValueError(f"Insufficient training samples after HMM filtering: {len(df_train)}")

    # Fill NaN values with 0 for features (conservative approach)
    X = df_train[feature_cols].fillna(0).values
    y = df_train['y_class'].values

    # Purged K-Fold cross-validation for OOF scores
    logger.info("Performing purged K-Fold CV for calibration")
    cv = PurgedKFold(
        n_splits=5,
        horizon=config['horizon_days'],
        embargo=config['embargo_days']
    )

    oof_scores = np.full(len(df_train), np.nan)
    oof_y = y.copy()

    for fold, (train_idx, val_idx) in enumerate(cv.split(df_train)):
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

    # Initialize results DataFrame
    results = pd.DataFrame(index=df_feat_today.index)

    # Handle HMM features with NaN
    # Only compute state probs for rows with valid HMM features
    df_hmm_valid = df_feat_today[art.hmm_feature_columns].dropna()

    # Initialize state prob columns with NaN
    n_states = art.hmm.n_states
    for i in range(n_states):
        results[f'state_prob_{i}'] = np.nan

    # Compute state probs for valid rows only
    if len(df_hmm_valid) > 0:
        Z_valid = df_hmm_valid.values
        state_probs_valid = art.hmm.transform(Z_valid)

        # Assign to valid indices
        for i in range(n_states):
            results.loc[df_hmm_valid.index, f'state_prob_{i}'] = state_probs_valid[:, i]

    # Prepare features for classifier
    df_with_states = df_feat_today.copy()
    for i in range(n_states):
        df_with_states[f'state_prob_{i}'] = results[f'state_prob_{i}']

    # Fill NaN with 0 and predict
    X = df_with_states[art.feature_columns].fillna(0).values
    p_up = art.clf.predict_proba(X)

    results['p_up'] = p_up

    # Add volatility for position sizing
    if 'rv_20d' in df_feat_today.columns:
        results['vol20_ann'] = df_feat_today['rv_20d']

    logger.info(f"Generated predictions for {len(results)} symbols ({len(df_hmm_valid)} with valid HMM states)")

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
    
    # Get latest dates from both stores
    feat_dates = sorted(feat_store.list_dates(), reverse=True)
    label_dates = sorted(label_store.list_dates(), reverse=True)

    if not feat_dates or not label_dates:
        logger.error("No features or labels available")
        return

    logger.info(f"Available feature dates: {feat_dates}")
    logger.info(f"Available label dates: {label_dates}")

    # Find first feature date with valid data (no all-NaN columns)
    df_feat_all = None
    selected_feat_date = None
    for feat_date in feat_dates:
        df_temp = feat_store.read(feat_date)
        # Check if HMM features have valid data
        hmm_cols = ['ret_1d', 'ret_5d', 'ret_20d', 'rv_20d', 'mom_1m', 'mom_3m', 'sox_chg_5d', 'sox_chg_20d']
        valid_cols = [c for c in hmm_cols if c in df_temp.columns and df_temp[c].notna().sum() > 0]
        if len(valid_cols) >= 6:  # At least 6 of 8 HMM features should be valid
            df_feat_all = df_temp
            selected_feat_date = feat_date
            logger.info(f"Using features from {selected_feat_date} (has {len(valid_cols)} valid HMM features)")
            break

    if df_feat_all is None:
        logger.error("No valid feature data found")
        return

    df_labels = label_store.read(label_dates[0])

    # Filter features to only include dates that are in labels
    label_dates_set = set(df_labels.index.get_level_values('as_of_date'))
    df_feat = df_feat_all[df_feat_all.index.get_level_values('as_of_date').isin(label_dates_set)]

    if args.train:
        logger.info("Training mode")
        logger.info(f"Training on {len(df_feat)} feature rows and {len(df_labels)} label rows")

        artifacts = fit_pipeline(df_feat, df_labels, config)

        # Save artifacts with pickle
        model_path = Path("data") / "models" / "artifacts.pkl"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(artifacts, f)
        logger.info(f"Saved artifacts to {model_path}")
        logger.info("Training complete")

    if args.score:
        logger.info("Scoring mode")
        # Load artifacts from storage
        model_path = Path("data") / "models" / "artifacts.pkl"
        if not model_path.exists():
            logger.error("Scoring requires saved artifacts - none found")
            return

        with open(model_path, 'rb') as f:
            artifacts = pickle.load(f)
        logger.info(f"Loaded artifacts from {model_path}")

        # Use the proper score_pipeline function
        results_df = score_pipeline(artifacts, df_feat_all)

        # Write predictions
        pred_store = PredictionStore(config['paths']['preds'])
        predictions = []

        for (as_of_date, symbol), row in results_df.iterrows():
            # Extract state probabilities
            n_states = config['hmm']['n_states']
            state_probs = [float(row.get(f'state_prob_{i}', 0.0)) for i in range(n_states)]

            # Get volatility for position sizing
            vol20_ann = float(row.get('vol20_ann', 0.015))

            # Simple position sizing: inverse volatility scaling
            base_weight = 0.10  # 10% base allocation
            weight_suggested = base_weight * (0.015 / max(vol20_ann, 0.001))
            weight_suggested = min(weight_suggested, 0.20)  # Cap at 20%

            # Estimate expected excess return in bps
            # Rough heuristic: p_up maps to expected return
            p_up = float(row['p_up'])
            er20_hat_bps = (p_up - 0.5) * 200  # ±100 bps for ±50% prob

            predictions.append({
                'as_of_date': as_of_date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'p_up': p_up,
                'er20_hat_bps': er20_hat_bps,
                'state_probs': state_probs,
                'vol20_ann': vol20_ann,
                'weight_suggested': weight_suggested,
                'model_version': '0.1.0',
                'degraded': False
            })

        # Write predictions to disk
        pred_df = pd.DataFrame(predictions)
        if len(pred_df) > 0:
            pred_df['as_of_date'] = pd.to_datetime(pred_df['as_of_date'])
            latest_date = pred_df['as_of_date'].max().strftime('%Y-%m-%d')

            # Convert to MultiIndex format expected by pred_store
            pred_df = pred_df.set_index(['as_of_date', 'symbol'])
            pred_store.write(pred_df, latest_date)
            logger.info(f"Written {len(pred_df)} predictions for {latest_date}")


if __name__ == "__main__":
    main()
