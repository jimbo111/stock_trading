# Korean Semiconductors Quant Engine

Quantitative trading system for predicting 20-day excess returns of Samsung (005930.KS) and SK hynix (000660.KS) against KOSPI. Combines Hidden Markov Models for regime detection with calibrated Elastic Net classifiers for directional prediction.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pre-commit install

# Run with sample data
make sample-backtest

# Launch dashboard
uvicorn app:app --reload --port 3000

# Launch ML API
make run-api  # http://127.0.0.1:8000/docs
```

**Requirements:** Python 3.11+ | macOS/Linux | black + ruff

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML / Stats | scikit-learn, hmmlearn, numpy, pandas |
| Data | yfinance, Parquet stores, JSON schema validation |
| API | FastAPI, Pydantic, Uvicorn |
| Dashboard | Bootstrap 5.3, HTMX, Alpine.js |
| Dev Tools | pytest, black, ruff, pre-commit |

## Architecture

```
Raw Data (5 sources) → ETL Pipeline → Feature Store (Parquet)
                                            ↓
                         Labels ← Label Generator (20D excess return)
                            ↓
                Purged K-Fold CV → HMM + Elastic Net Classifier
                            ↓
                   Model Artifacts → Daily Scoring
                            ↓
                  Prediction Store → FastAPI REST API
                            ↓
                     Web Dashboard (Bootstrap + HTMX)
```

## Feature Engineering

**30+ features** across 8 categories, all z-scored with expanding window (t-1) to prevent lookahead bias:

- **Returns & Momentum** — 1d, 5d, 20d returns; 1m–12m momentum with 5-day skip
- **Volatility & Risk** — 20-day realized vol, 60-day drawdown, beta, idiosyncratic vol
- **Currency** — USD/KRW changes at 1d, 5d, 20d horizons
- **Semiconductors** — DRAM/NAND spot prices, SOX index changes
- **Flow Data** — KRX foreign net flows normalized by ADV
- **Macro** — Korea semiconductor exports with exponential decay (20-day half-life)
- **Missing Indicators** — Binary flags for NaN-status of each feature

## Modeling

### HMM Regime Detection
- 3-state Gaussian HMM identifies bear/neutral/bull market regimes
- Fitted on 8 technical features (returns, volatility, momentum, SOX)
- Outputs soft state probabilities that augment the classifier's feature set

### Elastic Net Classifier
- L1+L2 regularized logistic regression (C=1.0, l1_ratio=0.3, saga solver)
- **Isotonic calibration** on out-of-fold scores for reliable probability estimates
- Features: original 30+ engineered features + 3 HMM state probabilities

### Leakage Prevention
- **Purged K-Fold CV** (Lopez de Prado) — 5-fold with 20-day horizon purge + 20-day embargo
- **Expanding window z-scores** — each date normalized using only t-1 data
- **Forward-looking labels** — 20-day excess returns with proper alignment

## API Endpoints

```
GET  /v1/health                           → { status, version }
GET  /v1/predict?symbol=005930.KS         → single prediction
GET  /v1/predictions?as_of_date=YYYY-MM-DD → all predictions for date
GET  /v1/dates                            → available prediction dates
GET  /docs                                → Swagger/OpenAPI UI
```

**Prediction response:**
```json
{
  "symbol": "005930.KS",
  "as_of_date": "2025-01-15",
  "p_up": 0.62,
  "er20_hat_bps": 24.0,
  "state_probs": [0.15, 0.55, 0.30],
  "vol20_ann": 0.28,
  "weight_suggested": 0.045,
  "model_version": "0.1.0",
  "degraded": false
}
```

## Web Dashboard

Control server at `http://localhost:3000` with 5 pipeline buttons:

1. **Build Features** — runs ETL pipeline, stores to Parquet
2. **Generate Labels** — computes 20-day forward excess returns
3. **Train Model** — HMM + classifier with purged CV
4. **Score** — generates predictions for latest date
5. **Start API** — launches ML API on port 8000

Built with Bootstrap 5.3 + HTMX for background requests + Alpine.js for reactive status updates.

## Repository Structure

```
stock_trading/
├── api/                    # FastAPI REST application
│   ├── main.py             # Endpoints + CORS + error handling
│   └── schemas.py          # Pydantic request/response models
├── app.py                  # Dashboard control server (port 3000)
├── backtest/               # Backtesting engine (WIP)
├── config/
│   └── default.yaml        # Central configuration (symbols, params, paths)
├── data_contracts/         # JSON schemas for data validation
├── etl/
│   ├── feature_defs.py     # 30+ feature definitions (359 lines)
│   └── build_features.py   # Pipeline entry point
├── frontend/               # Dashboard UI (Bootstrap + HTMX + Alpine.js)
├── labeling/
│   └── make_labels.py      # 20-day excess return labels
├── modeling/
│   ├── hmm.py              # 3-state Gaussian HMM
│   ├── classifier_enet.py  # Elastic Net with isotonic calibration
│   └── pipeline.py         # Training + scoring orchestration
├── samples/data/           # Sample CSVs for testing without external data
├── stores/                 # Parquet-based feature/label/prediction stores
├── tests/                  # pytest (CV, labels, HMM)
└── utils/                  # Calendar, purged CV, I/O, logging, timezones
```

## Configuration

`config/default.yaml`:

```yaml
symbols: ["005930.KS", "000660.KS"]  # Samsung, SK hynix
horizon_days: 20                      # Prediction horizon
kelly_frac: 0.25                      # Kelly fraction for sizing
weight_max: 0.05                      # Max position size
commission_bps: 2                     # Transaction cost
embargo_days: 20                      # CV embargo period
hmm:
  n_states: 3
  cov_type: "full"
model:
  C: 1.0
  l1_ratio: 0.3
```

## Testing

```bash
pytest -v                        # Run all tests
pytest --cov=. --cov-report=html # With coverage report
```

**Current coverage (~60%):**
- Purged K-Fold CV validation
- Label generation + edge cases
- HMM fitting and transform

## Expected Performance

| Metric | Target Range |
|--------|-------------|
| Information Ratio | 0.5 – 1.5 |
| Hit Rate | 52 – 58% |
| Annualized Turnover | 100 – 200% |
| Max Drawdown | 10 – 20% |

Performance depends on data quality, market regime, and parameter tuning. Always paper trade first.

## Key Design Decisions

- **Purged CV over time-series split** — prevents label leakage while maximizing data usage
- **HMM + classifier** — regime-aware predictions outperform static models in regime-shifting markets
- **Isotonic calibration** — ensures probability estimates match empirical frequencies
- **Parquet + JSON dual storage** — Parquet for analysis, JSON for API responses
- **Sample data included** — enables instant testing without external data sources

## Development

```bash
black .            # Format
ruff check . --fix # Lint
pytest -v          # Test
```

Pre-commit hooks auto-run black + ruff on every commit.

## References

- *Advances in Financial Machine Learning* (Lopez de Prado) — purged CV, metalabeling
- *Quantitative Trading* (Chan) — mean reversion, momentum strategies
- hmmlearn documentation — Gaussian HMM implementation
- scikit-learn calibration — isotonic regression

## License

Educational and research purposes. Trading involves risk of loss. The authors are not responsible for any financial losses incurred.

---

*Built for quantitative researchers and algo traders*
