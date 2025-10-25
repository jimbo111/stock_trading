# 🚀 Quick Start Guide - Korean Semiconductor Alpha Engine

## 5-Minute Demo

```bash
# 1. Navigate to project
cd semis-alpha-starter

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests to verify installation
pytest -v

# 5. Generate features from sample data
python etl/build_features.py --use-samples

# 6. Generate labels
python labeling/make_labels.py --use-samples

# 7. Start the API
make run-api
# Or: uvicorn api.main:app --reload --port 8000
```

## What Just Happened?

1. **Features Generated**: The system processed sample data and created 30+ engineered features
2. **Labels Generated**: Computed 20-day excess returns vs KOSPI
3. **API Started**: FastAPI server running at http://localhost:8000

## Explore the API

Open your browser to:
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Try these endpoints:
```bash
# Health check
curl http://localhost:8000/v1/health

# List available dates
curl http://localhost:8000/v1/dates

# Get predictions (will be empty until you train and score)
curl http://localhost:8000/v1/predictions
```

## Next Steps

### Step 1: Train a Model (30 minutes)

```bash
# This will train HMM + classifier on sample data
python modeling/pipeline.py --train --use-samples
```

**Note**: Model persistence is not yet implemented, so you'll need to modify `pipeline.py` to save artifacts.

### Step 2: Generate Predictions

Once models are trained and saved:

```bash
python modeling/pipeline.py --score --use-samples
```

### Step 3: View Predictions via API

```bash
curl http://localhost:8000/v1/predictions
curl "http://localhost:8000/v1/predict?symbol=005930.KS"
```

## Understanding the Data Flow

```
Sample CSVs → ETL → Features (Parquet) → Training → Models → Scoring → Predictions → API
   ↓
Labels (Parquet) ┘
```

## File Locations

- **Input**: `samples/data/*.csv`
- **Features**: `data/gold/dt=YYYY-MM-DD/features.parquet`
- **Labels**: `data/gold/dt=YYYY-MM-DD/labels.parquet`
- **Predictions**: `data/preds/dt=YYYY-MM-DD/predictions.json`

## Common Issues

### Issue: Import errors

**Solution**:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Module not found

**Solution**: Make sure you're in the project root and venv is activated:
```bash
pwd  # Should show .../semis-alpha-starter
which python  # Should show .venv/bin/python
```

### Issue: No predictions available

**Reason**: You haven't trained and scored models yet. The API serves cached predictions.

### Issue: Port 8000 already in use

**Solution**:
```bash
# Use different port
uvicorn api.main:app --port 8001
```

## Development Workflow

1. **Make Changes**: Edit code in your IDE
2. **Format**: `make format`
3. **Test**: `pytest -v`
4. **Run**: Test with sample data
5. **Commit**: Pre-commit hooks will run automatically

## Key Files to Modify First

When moving from samples to production:

1. **`etl/ingest_*.py`**: Add your data provider API calls
2. **`config/default.yaml`**: Update symbols, parameters
3. **`modeling/pipeline.py`**: Add model save/load
4. **`backtest/engine.py`**: Complete backtest implementation

## Sample Data Overview

The included samples contain:
- **8 trading days** (Sept 1-10, 2025)
- **2 stocks**: Samsung (005930.KS), SK hynix (000660.KS)
- **2 benchmarks**: KOSPI (^KS11), SOX (^SOX)
- **Price trend**: Slight uptrend (~3% over period)

This is enough to:
- Test the feature engineering
- Validate the data flow
- Ensure the API works

It's **NOT enough** to:
- Train a meaningful model (need years of data)
- Evaluate performance (need longer backtest)
- Go to production (need real-time data)

## Production Checklist

Before using with real money:

- [ ] Connect real data providers
- [ ] Backtest on 3-5 years of historical data
- [ ] Validate there's no lookahead bias
- [ ] Paper trade for 1-2 months
- [ ] Implement monitoring and alerts
- [ ] Add authentication to API
- [ ] Set up automated retraining
- [ ] Define risk limits
- [ ] Create disaster recovery plan

## Learning Path

### Week 1: Understanding
- Read the README thoroughly
- Study the sample data
- Understand the feature definitions
- Review the CV methodology

### Week 2: Integration
- Implement one data provider (start with Yahoo Finance)
- Load historical data (1 year minimum)
- Generate features and labels

### Week 3: Modeling
- Train models on historical data
- Validate performance metrics
- Tune hyperparameters

### Week 4: Backtesting
- Complete the backtest engine
- Run full historical backtest
- Analyze results (Sharpe, drawdown, turnover)

### Week 5-6: Production Prep
- Paper trade with live data
- Monitor for errors
- Refine based on results

### Week 7+: Live Trading
- Start with minimal capital
- Scale up gradually
- Monitor continuously

## Getting Help

1. **Check README.md**: Comprehensive documentation
2. **Check IMPLEMENTATION_SUMMARY.md**: Technical details
3. **Read docstrings**: All functions are documented
4. **Run tests**: See `tests/` for examples
5. **Check logs**: `logs/semis_alpha.log`

## Key Concepts to Understand

1. **Purged CV**: Why we need it (overlapping labels)
2. **Expanding Window**: Why z-score uses t-1 (prevent leakage)
3. **Excess Returns**: Stock return minus benchmark
4. **Kelly Criterion**: Position sizing methodology
5. **HMM States**: Market regime detection
6. **Calibration**: Making probabilities reliable

## Performance Expectations

With sample data:
- **Feature generation**: <1 second
- **Label generation**: <1 second
- **Model training**: 5-10 seconds (very small dataset)

With production data (5 years):
- **Feature generation**: 1-2 minutes
- **Label generation**: 30 seconds
- **Model training**: 5-15 minutes (with CV)
- **Daily scoring**: <5 seconds

## Tips for Success

1. **Start small**: Use 1 year of data first
2. **Validate everything**: Check for NaN, outliers, data quality
3. **Log liberally**: You'll thank yourself later
4. **Test constantly**: Add tests as you build
5. **Monitor production**: Set up alerts for anomalies
6. **Be patient**: Good quant strategies take time to develop

## Resources

- **Documentation**: See README.md
- **API Docs**: http://localhost:8000/docs (when running)
- **Sample Notebook**: `samples/notebooks/explore_samples.ipynb` (create this)
- **Tests**: `tests/` directory for examples

## Final Notes

This is a **starter skeleton**. You must:
1. Add real data connectors
2. Train on sufficient history
3. Validate thoroughly
4. Paper trade before going live

**Remember**: Past performance doesn't guarantee future results. Always test extensively and start small.

Happy trading! 📈
