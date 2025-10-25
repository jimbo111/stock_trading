# Stock Trading System - Usage Guide

## Overview
This system predicts 20-day excess returns for Korean semiconductor stocks (Samsung 005930.KS, SK Hynix 000660.KS) using HMM regime detection + Elastic Net classification.

---

## Demo Mode: Using Sample Data

### Step 1: Build Features
```bash
python -m etl.build_features --use-samples
```
**What it does:** 
- Loads sample market data from `samples/data/*.csv`
- Computes 23+ engineered features (returns, momentum, volatility, flows, etc.)
- Saves to `data/gold/dt=YYYY-MM-DD/features.parquet`

**Output:** 20 rows × 46 features saved to data/gold/

---

### Step 2: Generate Labels
```bash
python -m labeling.make_labels --use-samples
```
**What it does:**
- Loads sample price data
- Computes 20-day forward excess returns vs KOSPI
- Creates binary labels (positive/negative excess return)
- Saves to `data/gold/dt=YYYY-MM-DD/labels.parquet`

---

### Step 3: Train Model
```bash
python -m modeling.pipeline --train --use-samples
```
**What it does:**
- Loads features + labels
- Fits 3-state HMM for regime detection
- Trains calibrated Elastic Net classifier
- Uses Purged K-Fold cross-validation
- (NOTE: Model saving not yet implemented - see TODO in code)

---

### Step 4: Start API Server
```bash
uvicorn api.main:app --reload --port 8000
```
**What it does:**
- Starts REST API on http://localhost:8000
- Serves predictions from `data/preds/`

**Endpoints:**
- `GET /` - API documentation (Swagger UI)
- `GET /v1/health` - Health check
- `GET /v1/predict?symbol=005930.KS` - Single prediction
- `GET /v1/predictions?date=2024-01-15` - All predictions for date

---

## Production Mode: Using Your Own Data

### Required Data Sources

You need **5 CSV files** with the following structure:

#### 1. Market Prices (`market_prices.csv`)
```csv
as_of_date,symbol,open,high,low,close,volume
2024-01-02,005930.KS,72600,73400,72200,73000,12500000
2024-01-02,000660.KS,135000,137000,134500,136500,2500000
2024-01-02,^KS11,2600.50,2615.30,2598.20,2610.00,450000000
2024-01-02,^SOX,3850.25,3872.50,3842.10,3865.30,85000000
```
**Required symbols:**
- `005930.KS` - Samsung Electronics
- `000660.KS` - SK hynix  
- `^KS11` - KOSPI benchmark
- `^SOX` - Philadelphia Semiconductor Index

**Where to get:**
- Yahoo Finance API: `yfinance` library
- Korea Exchange (KRX): https://global.krx.co.kr
- Investing.com

---

#### 2. FX Rates (`fx_rates.csv`)
```csv
as_of_date,currency_pair,rate
2024-01-02,USDKRW,1295.50
2024-01-03,USDKRW,1298.20
```
**Where to get:**
- Bank of Korea: https://www.bok.or.kr
- FRED (St. Louis Fed): https://fred.stlouisfed.org
- Forex APIs: fixer.io, exchangerate-api.com

---

#### 3. Memory Prices (`memory_prices.csv`)
```csv
as_of_date,memory_type,price_usd
2024-01-02,DRAM_DDR4_8GB,2.45
2024-01-02,NAND_512GB,12.80
```
**Required types:**
- Any DRAM product (e.g., DDR4 8GB)
- Any NAND product (e.g., 512GB module)

**Where to get:**
- DRAMeXchange: https://www.dramexchange.com
- TrendForce
- Industry reports

---

#### 4. Korea Exports (`kr_exports.csv`)
```csv
as_of_date,category,value_usd_millions
2024-01-02,semiconductors,11250.5
2024-01-02,electronics,8320.3
```
**Required categories:**
- `semiconductors`
- `electronics`

**Where to get:**
- Korea Customs Service: https://www.customs.go.kr
- Korea International Trade Association (KITA): https://stat.kita.net
- Usually published monthly (system handles daily interpolation)

---

#### 5. Foreign Flows (`krx_flows.csv`)
```csv
as_of_date,symbol,foreign_buy_value,foreign_sell_value,net_flow,volume
2024-01-02,005930.KS,185000000000,172000000000,13000000000,12500000
2024-01-02,000660.KS,42000000000,38500000000,3500000000,2500000
```
**Where to get:**
- Korea Exchange (KRX): https://global.krx.co.kr
- Data providers: QuantConnect, Quandl

---

## Workflow for Production

### 1. Data Collection Script

Create `scripts/collect_data.py`:
```python
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Collect market data
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

---

### 2. Daily Pipeline (via Cron or Airflow)

```bash
#!/bin/bash
# daily_pipeline.sh

# 1. Collect fresh data
python scripts/collect_data.py

# 2. Build features
python -m etl.build_features

# 3. Generate labels (optional - only for training data)
python -m labeling.make_labels

# 4. Score today's data (requires saved model)
python -m modeling.pipeline --score

# 5. Restart API to serve new predictions
pkill -f uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
```

**Schedule with cron:**
```bash
# Run every day at 6 PM KST (after market close)
0 18 * * * /path/to/daily_pipeline.sh
```

---

### 3. Model Training (Weekly/Monthly)

```bash
# Collect historical data (last 2-3 years)
python scripts/collect_historical.py --years 3

# Build features for entire history
python -m etl.build_features

# Generate labels
python -m labeling.make_labels

# Train models
python -m modeling.pipeline --train

# Models saved to data/models/ (once implemented)
```

---

## Configuration

Edit `config/default.yaml` to customize:

```yaml
# Target stocks
symbols:
  - "005930.KS"  # Add/remove symbols
  - "000660.KS"

# Prediction horizon
horizon_days: 20  # Change to 10, 30, etc.

# Risk parameters
kelly_frac: 0.25
weight_max: 0.05

# Model settings
hmm:
  n_states: 3  # Try 2, 4, 5 states
  
model:
  C: 1.0  # Regularization
  l1_ratio: 0.3  # L1 vs L2 balance
```

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

---

## API Usage

Once the API is running:

```bash
# Check health
curl http://localhost:8000/v1/health

# Get prediction for Samsung
curl http://localhost:8000/v1/predict?symbol=005930.KS

# Get all predictions for a date
curl http://localhost:8000/v1/predictions?date=2024-01-15

# List available dates
curl http://localhost:8000/v1/dates
```

**Response example:**
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

## Data Frequency Requirements

| Data Type | Minimum Frequency | Recommended |
|-----------|------------------|-------------|
| Market Prices | Daily | Real-time |
| FX Rates | Daily | Daily |
| Memory Prices | Weekly | Daily |
| Korea Exports | Monthly | Monthly |
| Foreign Flows | Daily | Daily |

**Note:** The system handles missing data gracefully with forward-fill and decay.

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

## Troubleshooting

### "No module named hmmlearn"
```bash
pip install -r requirements.txt
```

### "No features found for date"
Make sure you ran `etl.build_features` first.

### "Model artifacts not found"
Model saving is not yet implemented. See `modeling/pipeline.py:225` TODO.

### "Insufficient data for HMM fitting"
Need at least 50 clean samples. Collect more historical data.

---

## Production Checklist

- [ ] Data collection scripts working
- [ ] Historical data loaded (2+ years)
- [ ] Features building successfully
- [ ] Model trained and saved
- [ ] API serving predictions
- [ ] Daily pipeline scheduled
- [ ] Monitoring/alerting set up
- [ ] Backup strategy in place

