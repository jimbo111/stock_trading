# 🚀 Quick Start Guide - Quant Trading Web Application

## Overview

This is an interactive web application dashboard for managing the complete ML pipeline for quantitative trading. Built with **Bootstrap 5.3**, **HTMX**, and **Alpine.js** on the frontend, with **FastAPI** on the backend.

---

## 📋 Prerequisites

- Python 3.11+
- FastAPI and Uvicorn (already in `requirements.txt`)
- All dependencies from `requirements.txt`

---

## ⚡ Quick Start (3 Steps)

### Step 1: Start the Control Server

```bash
# Run the control server on port 3000
uvicorn app:app --reload --port 3000
```

You should see:
```
========================================================
🚀 Stock Trading Quant Engine v1.0.0
========================================================
📍 Control Server: http://localhost:3000
📍 ML API Server: http://localhost:8000
📚 API Docs: http://localhost:8000/docs

💡 Technologies:
   • Frontend: Bootstrap 5.3 + HTMX + Alpine.js
   • Backend: FastAPI + Python
   • ML: scikit-learn + hmmlearn
========================================================
```

### Step 2: Open Dashboard in Browser

Go to: **http://localhost:3000**

You should see the dashboard with 5 pipeline control buttons.

### Step 3: Execute the Pipeline

Click the buttons in order:

1. **Step 1: Generate Features** ⚡
   - Processes sample market data
   - Creates 46 engineered features
   - ~30 seconds

2. **Step 2: Generate Labels** 🏷️
   - Computes 20-day excess returns
   - Prepares labels for training
   - ~5 seconds

3. **Step 3: Train Models** 🤖
   - Trains HMM (regime detection)
   - Trains Elastic Net classifier
   - Uses purged K-Fold cross-validation
   - ~10 seconds

4. **Step 4: Generate Predictions** 🎯
   - Creates predictions using trained models
   - Saves to `data/preds/`
   - ~5 seconds

5. **Step 5: Start API** 🚀
   - Starts ML API server on port 8000
   - Serves predictions via REST API
   - Click to start

---

## 🎨 Dashboard Features

### Left Sidebar (Pipeline Control)
- 5 pipeline execution buttons
- Current step indicator
- Status message display
- Progress indicator

### Main Content Area
- **Pipeline Status & Logs**: Real-time execution status
- **Results & Predictions**: Display generated predictions
- **Info Tabs**:
  - Application information
  - Pipeline step descriptions
  - API endpoint documentation

### Status Indicators
- 🟢 Success (Green)
- 🔵 Running (Blue)
- 🟠 Warning (Orange)
- 🔴 Error (Red)
- ⚪ Idle (Gray)

---

## 🌐 API Endpoints

Once the API server is running (Step 5):

### Health Check
```bash
curl http://localhost:8000/v1/health
```

### Get All Predictions
```bash
curl http://localhost:8000/v1/predictions
```

### Get Specific Stock Prediction
```bash
curl "http://localhost:8000/v1/predict?symbol=005930.KS"
```

### List Available Dates
```bash
curl http://localhost:8000/v1/dates
```

### API Documentation
Open in browser: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
stock_trading/
├── app.py                          # Control server (FastAPI)
├── frontend/                       # Web dashboard
│   ├── index.html                 # Main dashboard
│   ├── css/
│   │   └── style.css              # Bootstrap customization
│   ├── js/
│   │   └── app.js                 # Alpine.js logic
│   └── templates/                 # HTMX fragments
├── etl/                           # Feature engineering
├── labeling/                      # Label generation
├── modeling/                      # ML training & scoring
├── api/                           # Prediction API
├── data/                          # Data storage
├── TECH_STACK.md                  # Technology documentation
└── QUICKSTART.md                  # This file
```

---

## 🔧 Troubleshooting

### Port Already in Use

If port 3000 or 8000 is already in use:

```bash
# Find process using port 3000
lsof -i :3000

# Kill the process (replace PID with the process ID)
kill -9 <PID>

# Or use a different port
uvicorn app:app --reload --port 3001
```

### Module Not Found Errors

Ensure you're in the correct directory:

```bash
cd /path/to/stock_trading

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app:app --reload --port 3000
```

### Old Data Issues

If you get errors about data misalignment:

```bash
# Clean old data
rm -rf data/gold/dt=*
rm -rf data/preds/dt=*
rm -rf data/models/artifacts.pkl

# Then run the pipeline again
```

### API Not Responding

Make sure the API server is running:

1. Check the status on the dashboard (top right)
2. Verify port 8000 is free
3. Check console for error messages
4. Try accessing: http://localhost:8000/docs

---

## 📊 Sample Output

After running all 5 steps, you'll have:

- **Features**: 240 rows × 46 columns
- **Labels**: 200 rows with 46.5% positive class
- **Models**: HMM (3-state) + Elastic Net classifier
- **Predictions**: 200 predictions with confidence scores

---

## 🎯 Next Steps

### Phase 2: Enhanced Features
- [ ] WebSocket for live logs
- [ ] Progress bars for each step
- [ ] Error notifications
- [ ] Step execution history

### Phase 3: Advanced Features
- [ ] Prediction results table
- [ ] Performance charts
- [ ] Model metrics display
- [ ] Parameter tuning interface

### Phase 4: Production Ready
- [ ] Database integration
- [ ] User authentication
- [ ] Multi-model support
- [ ] Real data connectors

---

## 📚 Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Bootstrap** | 5.3.0 | UI Framework |
| **HTMX** | Latest | Dynamic interactions |
| **Alpine.js** | 3.x | Lightweight reactivity |
| **FastAPI** | Latest | Backend API |
| **Python** | 3.11+ | ML & backend |
| **scikit-learn** | Latest | Machine learning |
| **hmmlearn** | Latest | Hidden Markov Models |

---

## 🔗 Useful Links

- [Bootstrap Documentation](https://getbootstrap.com/docs/5.3/)
- [HTMX Documentation](https://htmx.org/)
- [Alpine.js Documentation](https://alpinejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 💡 Tips

1. **Keep the terminal open** where you run `uvicorn` to see logs
2. **Use browser DevTools** (F12) to debug HTMX requests
3. **Check console** for Alpine.js errors
4. **Monitor logs** for pipeline execution details
5. **Use API docs** at localhost:8000/docs to test endpoints

---

## 🐛 Reporting Issues

If you encounter issues:

1. Check the browser console (F12)
2. Check the terminal logs
3. Verify all ports are available
4. Try cleaning and rerunning the pipeline
5. Check `TECH_STACK.md` for detailed architecture

---

## 📄 License

This project is part of the Stock Trading Quant Engine.

---

**Happy Trading! 📈**

For more details, see `TECH_STACK.md` and `README.md`
