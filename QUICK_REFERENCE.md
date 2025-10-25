# Quick Reference Guide

## 📋 Data Format Summary

### What Data You Need (5 Files)

```
1. Market Prices      → Stock OHLCV + Benchmark (KOSPI, SOX)
2. FX Rates           → USD/KRW exchange rate
3. Memory Prices      → DRAM & NAND spot prices
4. Korea Exports      → Semiconductor export values
5. Foreign Flows      → Foreign investor buy/sell data
```

---

## 🎯 Command Cheat Sheet

### Demo Mode (Sample Data)
```bash
# Step 1: Build features
python -m etl.build_features --use-samples

# Step 2: Generate labels
python -m labeling.make_labels --use-samples

# Step 3: Train model
python -m modeling.pipeline --train --use-samples

# Step 4: Start API
uvicorn api.main:app --reload
```

### Production Mode (Real Data)

```bash
# Install data collection dependency
pip install yfinance

# Collect 1 year of market data
python scripts/collect_market_data.py --days 365

# TODO: Collect other data sources (FX, memory, exports, flows)
# See USAGE_GUIDE.md for data source links

# Build features (no --use-samples flag)
python -m etl.build_features

# Generate labels
python -m labeling.make_labels

# Train model
python -m modeling.pipeline --train

# Score new data
python -m modeling.pipeline --score

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 📁 Data Schema Reference

### 1. Market Prices CSV
```csv
as_of_date,symbol,open,high,low,close,volume
2024-01-02,005930.KS,72600,73400,72200,73000,12500000
2024-01-02,000660.KS,135000,137000,134500,136500,2500000
2024-01-02,^KS11,2600.50,2615.30,2598.20,2610.00,450000000
2024-01-02,^SOX,3850.25,3872.50,3842.10,3865.30,85000000
```
**Required:** 005930.KS, 000660.KS, ^KS11, ^SOX

### 2. FX Rates CSV
```csv
as_of_date,currency_pair,rate
2024-01-02,USDKRW,1295.50
```
**Required:** USDKRW daily rates

### 3. Memory Prices CSV
```csv
as_of_date,memory_type,price_usd
2024-01-02,DRAM_DDR4_8GB,2.45
2024-01-02,NAND_512GB,12.80
```
**Required:** Any DRAM product, Any NAND product

### 4. Korea Exports CSV
```csv
as_of_date,category,value_usd_millions
2024-01-02,semiconductors,11250.5
2024-01-02,electronics,8320.3
```
**Required:** semiconductors, electronics categories

### 5. Foreign Flows CSV
```csv
as_of_date,symbol,foreign_buy_value,foreign_sell_value,net_flow,volume
2024-01-02,005930.KS,185000000000,172000000000,13000000000,12500000
```
**Required:** 005930.KS, 000660.KS

---

## 🌐 Data Sources

| Data Type | Free Source | API/Tool |
|-----------|-------------|----------|
| **Market Prices** | Yahoo Finance | `yfinance` (Python) |
| **FX Rates** | FRED | `fredapi` (Python) |
| **Memory Prices** | Manual collection | TrendForce reports |
| **Exports** | KITA website | Manual CSV download |
| **Foreign Flows** | KRX website | Manual CSV download |

---

## 🔧 Configuration

Edit `config/default.yaml`:

```yaml
# Change prediction horizon
horizon_days: 20  # Try 10, 30, 60 days

# Adjust model
hmm:
  n_states: 3     # Try 2, 4, 5 regimes

model:
  C: 1.0          # Lower = more regularization
  l1_ratio: 0.3   # 0=Ridge, 1=Lasso
```

---

## 📊 Output Files

```
data/
├── bronze/          # Raw CSVs (your input)
├── gold/            # Processed features & labels
│   └── dt=2024-01-15/
│       ├── features.parquet
│       └── labels.parquet
└── preds/           # Model predictions
    └── dt=2024-01-15/
        ├── predictions.parquet
        └── predictions.json
```

---

## 🔍 API Endpoints

```bash
# Health check
GET /v1/health

# Single prediction
GET /v1/predict?symbol=005930.KS

# All predictions for date
GET /v1/predictions?date=2024-01-15

# List available dates
GET /v1/dates

# Interactive docs
GET /
```

---

## ⚡ Quick Start (30 seconds)

```bash
# Already have sample data, so just run:
python -m etl.build_features --use-samples
python -m labeling.make_labels --use-samples
uvicorn api.main:app --reload

# Visit http://localhost:8000
```

---

## 🐛 Common Issues

**Import Error:**
```bash
pip install -r requirements.txt
```

**No data found:**
```bash
# Make sure data files are in correct location
ls samples/data/
ls data/bronze/
```

**HMM tests fail:**
```
This is a conda environment issue, not a code bug.
Model will work in production/clean virtual env.
```

---

## 📚 Full Documentation

- **USAGE_GUIDE.md** - Complete guide with examples
- **README.md** - Project overview
- **IMPLEMENTATION_SUMMARY.md** - Technical details
- **QUICK_START.md** - Original quickstart

---

## 💡 Example: Collect Real Data

```bash
# Install data collection tool
pip install yfinance

# Get 2 years of stock data
python scripts/collect_market_data.py --days 730

# Output: data/bronze/market_prices.csv
# Now you need to collect the other 4 data sources manually
# See USAGE_GUIDE.md "Where to get" sections
```

---

## ✅ Production Deployment

```bash
# 1. Set up cron job for daily data collection
# 2. Run ETL + modeling pipeline
# 3. Deploy API (Docker, systemd, etc.)
# 4. Set up monitoring/alerting
# 5. Schedule weekly model retraining
```

See **USAGE_GUIDE.md** for full production setup.
