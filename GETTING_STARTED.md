# Getting Started - Korean Semiconductor Alpha Engine

Complete guide to setup, usage, and running the quantitative trading system.

---

## Table of Contents

1. [Quick Start (5 Minutes)](#quick-start-5-minutes)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage - Demo Mode (Sample Data)](#usage---demo-mode-sample-data)
5. [Usage - Production Mode (Real Data)](#usage---production-mode-real-data)
6. [Command Reference](#command-reference)
7. [Data Requirements](#data-requirements)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## Quick Start (5 Minutes)

Get up and running with sample data:

```bash
# 1. Setup environment
cd stock_trading
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Verify installation
pytest -v

# 3. Generate features and labels from sample data
python etl/build_features.py --use-samples
python labeling/make_labels.py --use-samples

# 4. Start the API server
uvicorn api.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```

**Or use the Web Dashboard:**

```bash
# Start control server
uvicorn app:app --reload --port 3000

# Open browser to: http://localhost:3000
# Click the 5 pipeline buttons in order
```

---

## Installation

### Prerequisites

- Python 3.11+ installed
- Git repository cloned
- Terminal/command line access

### Step-by-Step Setup

```bash
# 1. Navigate to project directory
cd /path/to/stock_trading

# 2. Verify Python version
python --version  # Should be 3.11+

# 3. Create virtual environment
python -m venv .venv

# 4. Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Setup pre-commit hooks (for development)
pre-commit install

# 7. Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Verify Installation

```bash
# Test all critical imports
python -c "
from utils.calendar import KRXCalendar
from utils.cv import PurgedKFold
from modeling.hmm import CycleHMM
from stores.feature_store import FeatureStore
from etl.build_features import load_sample_data
from labeling.make_labels import make_excess_return_labels
print('✅ All imports successful!')
"

# Run unit tests
pytest -v
```

**Requirements:** Python 3.11+ • OS: Linux/macOS • Style: black + ruff

---

## Configuration

Edit `config/default.yaml` to customize:

```yaml
# Target stocks
symbols:
  - "005930.KS"  # Samsung
  - "000660.KS"  # SK hynix

# Prediction parameters
horizon_days: 20           # Try 10, 30, 60 days
kelly_frac: 0.25          # Kelly fraction for position sizing
weight_max: 0.05          # Maximum position size
commission_bps: 2         # Transaction cost in basis points
embargo_days: 20          # CV embargo period

# Model settings
hmm:
  n_states: 3             # Try 2, 4, 5 regimes

model:
  C: 1.0                  # Lower = more regularization
  l1_ratio: 0.3           # 0=Ridge, 1=Lasso
```

Logging configuration: `config/logging.yaml`

---

## Usage - Demo Mode (Sample Data)

### Step 1: Generate Features

```bash
python etl/build_features.py --use-samples
```

**What it does:**
- Loads sample market data from `samples/data/*.csv`
- Computes 30+ engineered features (returns, momentum, volatility, flows, etc.)
- Saves to `data/gold/dt=YYYY-MM-DD/features.parquet`

**Output:** ~20 rows × 46 features

### Step 2: Generate Labels

```bash
python labeling/make_labels.py --use-samples
```

**What it does:**
- Loads sample price data
- Computes 20-day forward excess returns vs KOSPI
- Creates binary labels (positive/negative excess return)
- Saves to `data/gold/dt=YYYY-MM-DD/labels.parquet`

### Step 3: Train Model

```bash
python modeling/pipeline.py --train --use-samples
```

**What it does:**
1. Merges features + labels
2. Fits 3-state Gaussian HMM for regime detection
3. Augments features with HMM state probabilities
4. Trains Elastic Net classifier with purged 5-fold CV
5. Calibrates predictions using isotonic regression

**Note:** Model persistence is not yet implemented - see TODO in `modeling/pipeline.py:225`

### Step 4: Start API Server

```bash
uvicorn api.main:app --reload --port 8000
```

**Endpoints:**
- `GET /v1/health` - Health check
- `GET /v1/predict?symbol=005930.KS` - Single prediction
- `GET /v1/predictions` - All latest predictions
- `GET /v1/dates` - List available dates
- `GET /docs` - Interactive API documentation

**Test it:**
```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/predictions
curl "http://localhost:8000/v1/predict?symbol=005930.KS"
```

---

## Usage - Production Mode (Real Data)

### Data Requirements

You need **5 CSV files** with the following structure:

#### 1. Market Prices (`data/bronze/market_prices.csv`)

```csv
as_of_date,symbol,open,high,low,close,volume
2024-01-02,005930.KS,72600,73400,72200,73000,12500000
2024-01-02,000660.KS,135000,137000,134500,136500,2500000
2024-01-02,^KS11,2600.50,2615.30,2598.20,2610.00,450000000
2024-01-02,^SOX,3850.25,3872.50,3842.10,3865.30,85000000
```

**Required symbols:** 005930.KS (Samsung), 000660.KS (SK hynix), ^KS11 (KOSPI), ^SOX (SOX Index)

**Data sources:**
- Yahoo Finance: `yfinance` library (Python)
- Korea Exchange (KRX): https://global.krx.co.kr
- Investing.com

#### 2. FX Rates (`data/bronze/fx_rates.csv`)

```csv
as_of_date,currency_pair,rate
2024-01-02,USDKRW,1295.50
2024-01-03,USDKRW,1298.20
```

**Data sources:**
- Bank of Korea: https://www.bok.or.kr
- FRED (St. Louis Fed): https://fred.stlouisfed.org
- Forex APIs: fixer.io, exchangerate-api.com

#### 3. Memory Prices (`data/bronze/memory_prices.csv`)

```csv
as_of_date,memory_type,price_usd
2024-01-02,DRAM_DDR4_8GB,2.45
2024-01-02,NAND_512GB,12.80
```

**Required types:** Any DRAM product, Any NAND product

**Data sources:**
- DRAMeXchange: https://www.dramexchange.com
- TrendForce
- Industry reports (manual collection)

#### 4. Korea Exports (`data/bronze/kr_exports.csv`)

```csv
as_of_date,category,value_usd_millions
2024-01-02,semiconductors,11250.5
2024-01-02,electronics,8320.3
```

**Required categories:** semiconductors, electronics

**Data sources:**
- Korea Customs Service: https://www.customs.go.kr
- Korea International Trade Association (KITA): https://stat.kita.net
- Usually published monthly (system handles daily interpolation)

#### 5. Foreign Flows (`data/bronze/krx_flows.csv`)

```csv
as_of_date,symbol,foreign_buy_value,foreign_sell_value,net_flow,volume
2024-01-02,005930.KS,185000000000,172000000000,13000000000,12500000
2024-01-02,000660.KS,42000000000,38500000000,3500000000,2500000
```

**Data sources:**
- Korea Exchange (KRX): https://global.krx.co.kr
- Data providers: QuantConnect, Quandl

### Example: Collect Real Data

```python
# scripts/collect_data.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def collect_market_data(start_date, end_date):
    symbols = ['005930.KS', '000660.KS', '^KS11', '^SOX']

    dfs = []
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        df['symbol'] = symbol
        df = df.reset_index()
        df.rename(columns={'Date': 'as_of_date', 'Open': 'open',
                          'High': 'high', 'Low': 'low',
                          'Close': 'close', 'Volume': 'volume'}, inplace=True)
        dfs.append(df)

    result = pd.concat(dfs)
    result.to_csv('data/bronze/market_prices.csv', index=False)
    print(f"Collected {len(result)} market price rows")

# Run daily
if __name__ == '__main__':
    end_date = datetime.now()
    start_date = end_date - timedelta(days=400)  # ~1 year + buffer

    collect_market_data(start_date, end_date)
    # Add similar functions for FX, memory, exports, flows
```

### Production Workflow

```bash
# 1. Collect fresh data (daily)
python scripts/collect_data.py

# 2. Build features (no --use-samples flag)
python etl/build_features.py

# 3. Generate labels (optional - only for training data)
python labeling/make_labels.py

# 4. Score today's data (requires saved model)
python modeling/pipeline.py --score

# 5. Restart API to serve new predictions
pkill -f uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
```

### Model Training (Weekly/Monthly)

```bash
# Collect historical data (last 2-3 years)
python scripts/collect_historical.py --years 3

# Build features for entire history
python etl/build_features.py

# Generate labels
python labeling/make_labels.py

# Train models
python modeling/pipeline.py --train

# Models saved to data/models/ (once implemented)
```

### Schedule with Cron

```bash
# daily_pipeline.sh
#!/bin/bash

# 1. Collect fresh data
python scripts/collect_data.py

# 2. Build features
python -m etl.build_features

# 3. Score today's data
python -m modeling.pipeline --score

# 4. Restart API
pkill -f uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Schedule: Run every day at 6 PM KST (after market close)
# 0 18 * * * /path/to/daily_pipeline.sh
```

---

## Command Reference

### Quick Commands

```bash
# Demo Mode (Sample Data)
python -m etl.build_features --use-samples
python -m labeling.make_labels --use-samples
python -m modeling.pipeline --train --use-samples
uvicorn api.main:app --reload

# Production Mode (Real Data)
pip install yfinance
python scripts/collect_market_data.py --days 365
python -m etl.build_features
python -m labeling.make_labels
python -m modeling.pipeline --train
python -m modeling.pipeline --score
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_cv.py -v

# With coverage
pytest --cov=. --cov-report=html

# Run with debug logging
export LOG_LEVEL=DEBUG
python -m etl.build_features --use-samples
```

### Development

```bash
# Format code
make format

# Lint code
make lint

# Run sample backtest
make sample-backtest

# Start API
make run-api

# Clean data
make clean
```

---

## Data Requirements

### Data Frequency

| Data Type | Minimum Frequency | Recommended |
|-----------|------------------|-------------|
| Market Prices | Daily | Real-time |
| FX Rates | Daily | Daily |
| Memory Prices | Weekly | Daily |
| Korea Exports | Monthly | Monthly |
| Foreign Flows | Daily | Daily |

**Note:** The system handles missing data gracefully with forward-fill and decay.

### Data Quality

- **Market Prices**: At least 2 years of daily data for training
- **FX Rates**: Daily USD/KRW rates
- **Memory Prices**: Weekly DRAM and NAND spot prices
- **Exports**: Monthly semiconductor export values
- **Foreign Flows**: Daily foreign investor buy/sell data

---

## Troubleshooting

### Import Errors

```bash
# Solution: Install dependencies
pip install -r requirements.txt

# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Module Not Found

```bash
# Make sure you're in project root
pwd  # Should be /path/to/stock_trading
ls config/  # Should see default.yaml

# Activate virtual environment
source .venv/bin/activate
```

### HMM Training Fails

```
AttributeError: 'NoneType' object has no attribute 'get_capping'
```

This is a known conda/threadpoolctl issue, not a code bug. The code is correct.

**Solutions:**
1. Use clean virtual environment (not conda)
2. Update threadpoolctl: `pip install --upgrade threadpoolctl`
3. Ignore for now if testing with sample data

### API Returns "No predictions found"

This is expected - you need to:
1. Train model (Step 3)
2. Run scoring: `python -m modeling.pipeline --score --use-samples`
3. Note: Model saving is not yet implemented (see TODO in code)

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill the process (replace PID)
kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 8001
```

### Old Data Issues

```bash
# Clean old data
rm -rf data/gold/dt=*
rm -rf data/preds/dt=*
rm -rf data/models/artifacts.pkl

# Then run the pipeline again
```

### Sample Data Not Found

```bash
# Check that sample CSVs exist
ls samples/data/

# Should see:
# market_prices.sample.csv
# fx_rates.sample.csv
# memory_prices.sample.csv
# kr_exports.sample.csv
# krx_flows.sample.csv
```

### Tests Failing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run with verbose output
pytest -vv

# Check specific test
pytest tests/test_cv.py -vv
```

---

## Production Checklist

### Before Going Live

- [ ] **Data Providers**: Real data connectors implemented in `etl/ingest_*.py`
- [ ] **Historical Data**: 2-3 years of data collected
- [ ] **Feature Validation**: All features building successfully
- [ ] **Model Training**: Models trained and saved
- [ ] **Backtesting**: 3-5 years historical backtest completed
- [ ] **Model Persistence**: Save/load functionality implemented
- [ ] **API Running**: Predictions being served correctly
- [ ] **Daily Pipeline**: Scheduled with cron or Airflow
- [ ] **Monitoring**: Logging and alerting set up
- [ ] **Paper Trading**: 1-2 months of paper trading completed
- [ ] **Authentication**: API authentication implemented
- [ ] **Backup Strategy**: Data and model backup in place
- [ ] **Risk Limits**: Position size and risk limits defined
- [ ] **Disaster Recovery**: Recovery plan documented

### Development Timeline

**Week 1: Data Integration**
- Day 1-2: Implement market data ingestion
- Day 3-4: Implement FX, memory, exports ingestion
- Day 5: Implement flow data ingestion

**Week 2: Training & Backtest**
- Day 1-2: Add model serialization + MLflow
- Day 3-5: Complete backtest engine

**Week 3: Validation & Testing**
- Day 1-2: Comprehensive testing
- Day 3-4: Validation with historical data
- Day 5: Performance optimization

**Week 4: Deployment**
- Day 1-2: Docker setup
- Day 3-4: CI/CD pipeline
- Day 5: Production deployment

---

## Output Files

### Features: `data/gold/dt=YYYY-MM-DD/features.parquet`
- 46 columns (23 features + 23 missing indicators)
- MultiIndex: [as_of_date, symbol]
- Used for training and scoring

### Labels: `data/gold/dt=YYYY-MM-DD/labels.parquet`
- Columns: y_excess_return_20d, y_class
- Only needed for training

### Predictions: `data/preds/dt=YYYY-MM-DD/predictions.json`
- Probability of positive 20D excess return
- HMM state probabilities
- Suggested portfolio weights
- Served via API

### API Response Example

```json
{
  "symbol": "005930.KS",
  "as_of_date": "2024-01-15",
  "p_up": 0.62,
  "state_probs": [0.15, 0.55, 0.30],
  "vol20_ann": 0.28,
  "weight_suggested": 0.045,
  "model_version": "v1.0",
  "degraded": false
}
```

---

## Next Steps

1. **Test with sample data** (already done!)
2. **Set up data collection** for 1 month
3. **Build historical features** (2+ years)
4. **Train initial model**
5. **Deploy API** to production
6. **Schedule daily pipeline**
7. **Monitor performance**

---

## Support

For issues, questions, or contributions:

1. Check existing documentation (README.md, WEB_DASHBOARD.md, IMPLEMENTATION.md)
2. Check logs: `logs/semis_alpha.log`
3. Run tests: `pytest -vv`
4. Check API docs: http://localhost:8000/docs (when running)
5. Open a GitHub issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS)

---

**Remember:** This is a starter skeleton. You must implement:
1. Real data connectors in `etl/ingest_*.py`
2. Model serialization in `modeling/pipeline.py`
3. Complete backtest in `backtest/engine.py`
4. Production deployment infrastructure

**Start with the sample data, validate the approach, then integrate your real data sources.**

Good luck! 🚀
