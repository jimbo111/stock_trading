# 🚀 How to Run the Quant Trading Web Application

## 📋 Quick Reference

### **In 2 Commands:**

```bash
# Terminal 1: Start Control Server
uvicorn app:app --reload --port 3000

# Then open in browser:
# http://localhost:3000
```

That's it! Click the 5 buttons to run the pipeline.

---

## 📖 Complete Setup Guide

### **Prerequisites**
- Python 3.11+
- All dependencies installed (`pip install -r requirements.txt`)
- Ports 3000 and 8000 available

### **Step 1: Clean Old Data (Optional)**

```bash
# Remove stale data from previous runs
rm -rf data/gold/dt=*
rm -rf data/preds/dt=*
rm -rf data/models/artifacts.pkl
```

### **Step 2: Start Control Server**

```bash
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

INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### **Step 3: Open Dashboard**

Open in your browser:

```
http://localhost:3000
```

You'll see the beautiful Bootstrap dashboard with 5 pipeline buttons.

### **Step 4: Execute Pipeline**

Click the buttons in order (top to bottom):

```
⚡ Step 1: Generate Features
   ↓
🏷️ Step 2: Generate Labels
   ↓
🤖 Step 3: Train Models
   ↓
🎯 Step 4: Generate Predictions
   ↓
🚀 Step 5: Start API
```

Each step takes 5-30 seconds. Watch the status panel for updates.

### **Step 5: View Results (Optional)**

Once all steps complete:

```bash
# Open API documentation
http://localhost:8000/docs

# Or test endpoints
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/predictions
curl "http://localhost:8000/v1/predict?symbol=005930.KS"
```

---

## 🎨 Dashboard Overview

### **Left Sidebar**
- 5 colored buttons (one per step)
- Current step indicator
- Status message display
- Disable during execution

### **Main Area**
- **Status Panel**: Real-time logs and messages
- **Results Panel**: Generated data display
- **Info Tabs**: Documentation and API details

### **Status Colors**
- 🟢 **Green**: Success
- 🔵 **Blue**: Running
- 🟠 **Orange**: Warning
- 🔴 **Red**: Error
- ⚪ **Gray**: Idle

---

## ⏱️ Expected Timing

| Step | Time | What It Does |
|------|------|------------|
| 1 | ~30s | Generate 46 features from market data |
| 2 | ~5s | Calculate 20-day excess returns |
| 3 | ~10s | Train HMM + Elastic Net models |
| 4 | ~5s | Generate predictions |
| 5 | ~10s | Start API server on port 8000 |
| **Total** | **~60s** | **Complete pipeline** |

---

## 🔍 Monitoring Execution

### **Browser Console (F12)**

Watch Alpine.js logs:

```javascript
// You'll see:
📊 Stock Trading Quant Engine - Initializing...
✅ API is running
ℹ️ Step 1: Generating features...
✅ Features generated!
// ... etc
```

### **Terminal Output**

Watch FastAPI logs:

```
INFO:     127.0.0.1:52703 - "POST /api/pipeline/features HTTP/1.1" 200
INFO:     127.0.0.1:52704 - "POST /api/pipeline/labels HTTP/1.1" 200
INFO:     127.0.0.1:52705 - "POST /api/pipeline/train HTTP/1.1" 200
```

### **File System**

Generated data appears in:

```
data/
├── gold/
│   ├── dt=2024-05-20/
│   │   ├── features.parquet      (Step 1)
│   │   └── labels.parquet        (Step 2)
│   └── models/
│       └── artifacts.pkl         (Step 3)
└── preds/
    └── dt=2024-05-20/
        └── predictions.json      (Step 4)
```

---

## 🐛 Troubleshooting

### **Problem: Port 3000 Already in Use**

```bash
# Find what's using port 3000
lsof -i :3000

# Kill it (replace PID)
kill -9 <PID>

# Or use different port
uvicorn app:app --reload --port 3001
```

### **Problem: Module Not Found**

```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Make sure you're in right directory
cd /path/to/stock_trading

# Check Python version
python --version  # Should be 3.11+
```

### **Problem: "API not running" warning**

This is normal if you haven't clicked Step 5 yet. Click "Step 5: Start API" to start the ML API server.

### **Problem: Old data causing errors**

```bash
# Clean everything
rm -rf data/

# Run pipeline again from scratch
```

### **Problem: Dashboard looks broken**

```bash
# Hard refresh browser
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)

# Or clear cache
F12 → DevTools → Storage → Clear All
```

---

## 📱 Using the Dashboard

### **To Execute Step 1:**

```
Click "⚡ Step 1: Generate Features" button
  ↓
Status shows "Step 1: Generating features..."
  ↓
Wait ~30 seconds
  ↓
Status shows "✅ Step 1 completed successfully!"
  ↓
Proceed to Step 2
```

### **To View Status:**

- Check the **Status Panel** on the right
- Watch the **Console (F12)** for detailed logs
- Check the **Terminal** for FastAPI logs

### **To View API Docs:**

Once Step 5 is running:

1. Click the "API Status" tab
2. Or visit: `http://localhost:8000/docs`

### **To Test API Directly:**

```bash
# Health check
curl http://localhost:8000/v1/health

# Get all predictions
curl http://localhost:8000/v1/predictions | jq .

# Get specific stock
curl "http://localhost:8000/v1/predict?symbol=005930.KS" | jq .
```

---

## 🛑 To Stop the Application

### **Stop Control Server**

In terminal where you ran `uvicorn`:

```bash
Press Ctrl+C
```

### **Stop ML API Server**

If you started Step 5, you need to stop it separately:

```bash
# In another terminal
lsof -i :8000
kill -9 <PID>

# Or wait until Step 5 completes and the process exits
```

---

## 📚 File Locations

### **Frontend Files**
```
frontend/
├── index.html          # Main dashboard HTML
├── css/style.css       # Bootstrap customization
└── js/app.js           # Alpine.js logic
```

### **Backend**
```
app.py                  # FastAPI control server
```

### **ML Pipeline**
```
etl/build_features.py   # Feature engineering
labeling/make_labels.py # Label generation
modeling/pipeline.py    # Training & predictions
api/main.py             # Prediction serving API
```

### **Documentation**
```
TECH_STACK.md           # Architecture & technologies
QUICKSTART.md           # Quick start guide
APPLICATION_BUILT.md    # What was created
RUN_APPLICATION.md      # This file
```

---

## 🎯 Example Usage Session

```bash
# Terminal 1
$ cd /path/to/stock_trading
$ uvicorn app:app --reload --port 3000
INFO:     Uvicorn running on http://0.0.0.0:3000

# Browser
$ Open http://localhost:3000

# You see the dashboard with 5 buttons

# Click buttons in order:
1. Click "Step 1: Generate Features" → wait 30s → ✅ Success
2. Click "Step 2: Generate Labels" → wait 5s → ✅ Success
3. Click "Step 3: Train Models" → wait 10s → ✅ Success
4. Click "Step 4: Generate Predictions" → wait 5s → ✅ Success
5. Click "Step 5: Start API" → wait 10s → ✅ Success

# Now you have:
# - Generated 46 features
# - Generated labels
# - Trained models (HMM + Elastic Net)
# - Generated predictions
# - API running on port 8000

# Browser: Visit http://localhost:8000/docs
# Terminal: curl http://localhost:8000/v1/predictions
# Check: data/ folder for generated files
```

---

## 📊 What Happens Behind the Scenes

```
User clicks button
     ↓
HTMX POST to /api/pipeline/features
     ↓
FastAPI endpoint receives request
     ↓
BackgroundTasks.add_task() runs:
     subprocess.run(["python", "etl/build_features.py", "--use-samples"])
     ↓
Python script executes feature engineering
     ↓
Results saved to data/gold/dt=2024-05-20/features.parquet
     ↓
Response returned to browser
     ↓
HTMX swaps status panel with success message
     ↓
Alpine.js updates UI state
     ↓
User sees "✅ Step 1 completed!"
```

---

## 💡 Tips & Tricks

1. **Keep terminal open** - You'll see detailed logs
2. **Use browser DevTools (F12)** - Check for HTMX/Alpine errors
3. **Watch Network tab** - See HTTP requests to /api/pipeline/*
4. **Check Console** - See Alpine.js logs with timestamps
5. **Refresh page** - If UI gets stuck, hard refresh (Ctrl+Shift+R)
6. **Multiple browsers** - Open multiple instances of dashboard simultaneously

---

## 🔗 Important URLs

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Main dashboard |
| http://localhost:8000 | ML API (after Step 5) |
| http://localhost:8000/docs | Swagger API docs |
| http://localhost:8000/redoc | ReDoc API docs |

---

## ✅ Success Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Control Server running on port 3000
- [ ] Dashboard opens in browser
- [ ] Step 1 button works and generates features
- [ ] Step 2 button works and generates labels
- [ ] Step 3 button works and trains models
- [ ] Step 4 button works and generates predictions
- [ ] Step 5 button works and starts ML API
- [ ] API responds to http://localhost:8000/v1/health
- [ ] Data files appear in `data/` folder

---

## 📞 Need Help?

1. **Setup issues?** → Read QUICKSTART.md
2. **Architecture questions?** → Read TECH_STACK.md
3. **Browser issues?** → Open DevTools (F12)
4. **Server issues?** → Check terminal logs
5. **Data issues?** → Run `rm -rf data/` and start over

---

## 🎉 You're All Set!

Your interactive Quant Trading Web Application is ready to use.

**Next command to run:**

```bash
uvicorn app:app --reload --port 3000
```

Then open: **http://localhost:3000**

Happy trading! 📈
