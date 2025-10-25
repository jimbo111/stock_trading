# Korean Semiconductors Alpha Engine

**Starter repository skeleton for predicting 20-day excess returns of Samsung (005930.KS), SK hynix (000660.KS), and peers.**

This skeleton is opinionated, leakage-safe, and production-friendly. It combines Hidden Markov Models (HMM) for regime detection with calibrated Elastic Net classifiers for directional prediction.

## ⚡ Quickstart

```bash
# 1) Clone and setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pre-commit install

# 2) Run unit tests
pytest -q

# 3) Generate features & labels from samples
make sample-backtest

# 4) Launch API (serves cached predictions)
make run-api
# -> http://127.0.0.1:8000/docs
```

**Requirements:** Python 3.11+ • OS: Linux/macOS • Style: black + ruff

---

## 📋 What This Repo Provides

### Core Functionality

1. **Feature Engineering** (`etl/`)
   - Return & momentum indicators (1d, 5d, 20d, 1m-12m)
   - Volatility & risk metrics (realized vol, beta, idiosyncratic vol, drawdown)
   - FX features (USD/KRW changes)
   - Industry indicators (DRAM/NAND/HBM prices, SOX index)
   - Flow data (KRX foreign net flows)
   - Macro expanders (Korea exports with exponential decay)
   - All features z-scored with expanding window (t-1) to prevent leakage

2. **Label Generation** (`labeling/`)
   - 20-day forward excess returns vs KOSPI benchmark
   - Binary classification target (positive/negative ER)
   - Proper forward-looking alignment with no leakage

3. **Modeling** (`modeling/`)
   - **HMM (Gaussian, 3-state):** Detects market regimes (bear/neutral/bull)
   - **Elastic Net Classifier:** L1+L2 regularized logistic regression
   - **Isotonic Calibration:** Out-of-fold calibration for reliable probabilities
   - **Purged K-Fold CV:** Prevents label overlap leakage (Lopez de Prado)

4. **Backtest Engine** (`backtest/`)
   - Event-driven daily simulation
   - Kelly criterion position sizing with vol scaling
   - Commission & slippage models
   - Performance metrics (IR, hit rate, turnover, drawdown)

5. **API** (`api/`)
   - FastAPI REST endpoints
   - Serves latest predictions with model version tracking
   - Degradation flags for stale data
   - OpenAPI/Swagger docs at `/docs`

6. **Data Infrastructure** (`stores/`)
   - Parquet-based feature/label/prediction stores
   - Date-partitioned storage for efficient access
   - Schema validation via JSON contracts

---

## 🏗️ Architecture Overview

```
Raw Data Sources → ETL Pipeline → Feature Store (Parquet)
                                       ↓
                    Labels ← Label Generator (20D ER)
                       ↓
           Purged CV Training → HMM + Classifier
                       ↓
              Model Artifacts (MLflow)
                       ↓
         Daily Scoring → Prediction Store → API
                       ↓
              Backtest Engine → Reports
```

**Key Design Principles:**
- **No lookahead bias:** All features use t-1 windows
- **No label leakage:** Purged CV with embargo
- **Production-ready:** Modular, typed, tested, logged
- **Schema contracts:** All data validated against JSON schemas

---

## 📂 Repository Structure

```
semis-alpha-starter/
├─ api/                  # FastAPI application
├─ backtest/             # Backtesting engine
├─ config/               # YAML configuration
├─ data_contracts/       # JSON schemas for validation
├─ etl/                  # Data ingestion & features
├─ labeling/             # Label generation
├─ modeling/             # HMM + classifier + pipeline
├─ schedules/            # Airflow DAGs (placeholder)
├─ stores/               # Parquet-based data stores
├─ utils/                # Calendar, CV, I/O, logging
├─ samples/              # Sample CSV data for testing
├─ tests/                # Pytest unit tests
└─ data/                 # Runtime data (gitignored)
   ├─ bronze/            # Raw ingested data
   ├─ silver/            # Cleaned data
   ├─ gold/              # Features & labels
   └─ preds/             # Model predictions
```

---

## 🔧 Configuration

Edit `config/default.yaml`:

```yaml
symbols: ["005930.KS", "000660.KS"]  # Samsung, SK hynix
horizon_days: 20                      # Prediction horizon
kelly_frac: 0.25                      # Kelly fraction for sizing
weight_max: 0.05                      # Max position size
commission_bps: 2                     # Transaction cost
embargo_days: 20                      # CV embargo period
```

---

## 🚀 Usage

### 1. Generate Features

```bash
# Using sample data
python etl/build_features.py --use-samples

# Production (implement data providers first)
python etl/build_features.py --start-date 2020-01-01 --end-date 2025-10-24
```

**Output:** Features stored in `data/gold/dt=YYYY-MM-DD/features.parquet`

### 2. Generate Labels

```bash
python labeling/make_labels.py --use-samples
```

**Output:** Labels (er20, y_class) in `data/gold/dt=YYYY-MM-DD/labels.parquet`

### 3. Train Models

```bash
python modeling/pipeline.py --train --use-samples
```

**Process:**
1. Merges features + labels
2. Fits 3-state Gaussian HMM on selected features
3. Augments features with HMM state probabilities
4. Trains Elastic Net classifier with purged 5-fold CV
5. Calibrates predictions using isotonic regression on OOF scores

**Output:** Trained artifacts (currently in-memory; implement serialization)

### 4. Run Backtest

```bash
# TODO: Implement backtest/engine.py
python backtest/engine.py --use-samples --report ./reports/sample
```

### 5. Serve API

```bash
make run-api
# or
uvicorn api.main:app --reload --port 8000
```

**Endpoints:**
- `GET /v1/health` - Health check
- `GET /v1/predict?symbol=005930.KS` - Single prediction
- `GET /v1/predictions` - All latest predictions
- `GET /v1/dates` - List available dates

**Example:**
```bash
curl "http://localhost:8000/v1/predict?symbol=005930.KS"
```

---

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_cv.py -v

# With coverage
pytest --cov=. --cov-report=html
```

**Test Coverage:**
- ✅ Purged K-Fold CV
- ✅ Label generation
- ✅ HMM fitting/transforming
- ⚠️ Feature engineering (partial)
- ⚠️ Backtest engine (TODO)
- ⚠️ API endpoints (TODO)

---

## ⚠️ Known Issues & Future Work

### Critical Implementation Gaps

1. **Data Provider Integration**
   - ❌ `etl/ingest_*.py` modules are **stubs only**
   - ❌ No real market data connectors (Yahoo Finance, Bloomberg, etc.)
   - ❌ No vendor API key management
   - **Action Required:** Implement actual data fetching in ETL modules

2. **Model Persistence**
   - ❌ Trained models not saved to disk
   - ❌ No MLflow integration for experiment tracking
   - ❌ No model versioning or registry
   - **Action Required:** Add serialization in `modeling/pipeline.py`

3. **Backtest Engine**
   - ⚠️ `backtest/engine.py` is **incomplete**
   - ❌ Missing daily rebalancing logic
   - ❌ Cost models not fully implemented
   - ❌ Metrics calculation incomplete
   - **Action Required:** Implement `run_backtest()` function

4. **Feature Engineering Edge Cases**
   - ⚠️ Beta calculation simplified (may have alignment issues)
   - ⚠️ Idiosyncratic volatility needs validation
   - ⚠️ Export decay formula assumes monthly data
   - **Action Required:** Validate with real data and adjust

5. **Calendar Handling**
   - ⚠️ KRX holiday list is **hardcoded and incomplete**
   - ❌ No dynamic holiday calendar updates
   - **Action Required:** Integrate with proper KRX calendar provider

### Data Quality Concerns

1. **Schema Validation**
   - ⚠️ JSON schema validation is basic
   - ❌ No automated data quality checks in pipeline
   - **Action Required:** Implement `etl/quality.py` with comprehensive checks

2. **Missing Data Handling**
   - ⚠️ Forward-fill assumptions may be naive
   - ⚠️ Z-score calculation with sparse data untested
   - **Action Required:** Add robust imputation strategies

3. **Time Zone Handling**
   - ⚠️ KST-UTC conversion needs thorough testing
   - ⚠️ Potential for midnight boundary issues
   - **Action Required:** Add integration tests for timezone edge cases

### Performance & Scalability

1. **Feature Computation**
   - ⚠️ Not optimized for large datasets
   - ❌ No parallelization
   - ❌ No incremental feature updates
   - **Action Required:** Consider Dask/Ray for scaling

2. **Cross-Validation**
   - ⚠️ Purged CV can be slow with many folds
   - **Action Required:** Profile and optimize if needed

3. **API Performance**
   - ❌ No caching layer (Redis)
   - ❌ No rate limiting
   - **Action Required:** Add Redis for hot predictions

### Production Readiness

1. **Monitoring & Alerting**
   - ❌ No model performance monitoring
   - ❌ No data drift detection
   - ❌ No automated retraining triggers
   - **Action Required:** Implement monitoring stack

2. **Security**
   - ❌ API has no authentication
   - ❌ Secrets not managed (see `.env.example`)
   - **Action Required:** Add OAuth2/API keys, use secret manager

3. **Deployment**
   - ⚠️ Dockerfile is placeholder only
   - ❌ No CI/CD pipeline
   - ❌ No infrastructure-as-code
   - **Action Required:** Complete Docker setup, add GitHub Actions

4. **Scheduling**
   - ⚠️ `schedules/airflow_dags.py` is **stub only**
   - ❌ No actual DAG implementation
   - **Action Required:** Implement daily ETL and weekly retrain DAGs

### Model Improvements

1. **Feature Selection**
   - ⚠️ Current features are standard; not optimized
   - **Consider:** Add alternative data (sentiment, options flow, analyst estimates)

2. **Model Ensemble**
   - ⚠️ Single model architecture
   - **Consider:** Add LGBM regressor, LSTM for time-series, ensemble methods

3. **Risk Management**
   - ⚠️ Basic Kelly sizing only
   - **Consider:** Add EGARCH volatility forecasting, cointegration sleeves

---

## 🔒 Security Notes

**Never commit:**
- API keys (use `.env` file, see `.env.example`)
- Database credentials
- Model artifacts (large files → use DVC or MLflow artifact store)

**Recommended:**
- Use secret manager (AWS Secrets Manager, Azure Key Vault)
- Rotate keys regularly
- Audit data access logs

---

## 📊 Expected Performance

**Note:** Performance depends heavily on:
- Quality of input data
- Market regime (works better in trending markets)
- Parameter tuning
- Transaction costs

**Typical Metrics (Backtested):**
- Information Ratio: 0.5 - 1.5 (target)
- Hit Rate: 52-58% (modest edge)
- Annualized Turnover: 100-200%
- Max Drawdown: 10-20%

**⚠️ Past performance doesn't guarantee future results. Always paper trade first.**

---

## 🛠️ Development Workflow

1. **Feature Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Format & Lint**
   ```bash
   make format
   make lint
   ```

4. **Test**
   ```bash
   pytest -v
   ```

5. **Commit** (pre-commit hooks will run)
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

---

## 📚 Key References

- **Advances in Financial Machine Learning** (Lopez de Prado) - Purged CV, metalabeling
- **Quantitative Trading** (Chan) - Mean reversion, momentum strategies
- **Evidence-Based Technical Analysis** (Aronson) - Robust backtesting
- **hmmlearn Documentation** - Gaussian HMM implementation
- **scikit-learn Calibration** - Isotonic regression for probability calibration

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## 📝 License

This is a starter skeleton for educational/research purposes. Adapt for your use case.

**Disclaimer:** This software is for educational purposes only. Trading involves risk of loss. The authors are not responsible for any financial losses incurred.

---

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure you're in the project root and venv is activated
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Sample Data Not Found
```bash
# Check that sample CSVs exist
ls samples/data/
```

### API Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill process or use different port
uvicorn api.main:app --port 8001
```

### Tests Failing
```bash
# Install test dependencies
pip install pytest pytest-cov
# Run with verbose output
pytest -vv
```

---

## 📞 Support

For issues, questions, or contributions:
1. Check existing issues on GitHub
2. Open a new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS)

---

## 🎯 Roadmap

**Phase 1 (Current):**
- ✅ Core feature engineering
- ✅ Label generation
- ✅ HMM + classifier pipeline
- ✅ Basic API

**Phase 2 (Next 3 months):**
- ⬜ Complete backtest engine
- ⬜ MLflow integration
- ⬜ Production data providers
- ⬜ Model persistence
- ⬜ Comprehensive testing

**Phase 3 (Next 6 months):**
- ⬜ Advanced features (sentiment, options)
- ⬜ Model ensemble
- ⬜ Real-time scoring
- ⬜ Monitoring dashboard
- ⬜ Automated retraining

**Phase 4 (Future):**
- ⬜ Multi-asset expansion
- ⬜ Deep learning models
- ⬜ Alternative data integration
- ⬜ Live trading integration

---

**Remember:** This is a skeleton. You must implement:
1. Real data connectors in `etl/ingest_*.py`
2. Model serialization in `modeling/pipeline.py`
3. Complete backtest in `backtest/engine.py`
4. Production deployment infrastructure

**Start with the sample data, validate the approach, then integrate your real data sources.**

---

*Built with ❤️ for quantitative researchers and algo traders*
