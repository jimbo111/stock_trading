# Tech Stack - Stock Trading Quant Application

## Overview
A modern, interactive localhost web application for quantitative trading model development and deployment. The application provides a user-friendly interface to orchestrate the entire ML pipeline from feature engineering to prediction serving.

---

## Technology Stack

### **Backend**
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language for ML/quant algorithms |
| FastAPI | Latest | REST API framework for serving predictions |
| Uvicorn | Latest | ASGI application server |
| Pandas | Latest | Data manipulation and analysis |
| scikit-learn | Latest | Machine learning utilities |
| hmmlearn | Latest | Hidden Markov Models |

### **Frontend**
| Technology | Version | Purpose |
|------------|---------|---------|
| **Bootstrap** | 5.3+ | Responsive UI framework |
| **HTMX** | Latest | Dynamic HTML interactions without page reload |
| **Alpine.js** | Latest | Lightweight JavaScript framework for reactivity |
| **jQuery** | 3.7.1 | DOM manipulation (comes with Bootstrap) |
| **HTML5** | Latest | Semantic markup |
| **CSS3** | Latest | Styling and layout |
| **JavaScript (Vanilla + Alpine)** | ES6+ | Client-side logic |

### **Deployment**
| Technology | Purpose |
|------------|---------|
| Localhost | Development/testing environment |
| Python subprocess management | Running pipeline commands |

---

## Architecture

### **Two-Server Model**

```
┌─────────────────────────────────────────────────────────┐
│                    USER BROWSER                         │
│              (Localhost: port 3000/8080)                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Frontend (Bootstrap 5.3 + HTMX + Alpine.js)    │  │
│  │  - Dashboard UI                                  │  │
│  │  - Pipeline control panels                       │  │
│  │  - Real-time task status                         │  │
│  │  - Results visualization                         │  │
│  └──────────────────────────────────────────────────┘  │
│              ↕ HTTP/WebSocket ↕                        │
└─────────────────────────────────────────────────────────┘
                        ↓
            ┌───────────────────────┐
            │  Control Server       │
            │  (Flask/FastAPI)      │
            │  Port: 5000/8000      │
            │                       │
            │  - Orchestrates       │
            │    pipeline steps     │
            │  - Manages processes  │
            │  - Websocket updates  │
            └───────────────────────┘
                        ↓
        ┌───────────────────────────────┐
        │  ML Pipeline (subprocess)     │
        │                               │
        │  1. ETL/Features              │
        │  2. Labels                    │
        │  3. Training                  │
        │  4. Predictions               │
        │  5. API Server (port 8000)    │
        └───────────────────────────────┘
```

---

## Directory Structure

```
stock_trading/
├── frontend/                      # NEW - Frontend files
│   ├── index.html                # Main dashboard page
│   ├── css/
│   │   └── style.css             # Custom styles
│   ├── js/
│   │   ├── app.js                # Alpine.js app logic
│   │   └── api.js                # API client utilities
│   └── templates/                # HTMX template fragments
│       ├── pipeline-status.html
│       ├── feature-panel.html
│       ├── training-panel.html
│       └── results-panel.html
│
├── app.py                        # NEW - Control server (Flask/FastAPI)
│
├── api/                          # Existing - ML serving API
│   ├── main.py
│   └── schemas.py
│
├── etl/                          # Existing - Feature engineering
├── modeling/                     # Existing - ML training
├── labeling/                     # Existing - Label generation
├── data/                         # Existing - Data storage
└── TECH_STACK.md                # This file
```

---

## Frontend Component Details

### **Bootstrap 5.3**
- **Purpose**: Responsive grid system, pre-built components, consistent design
- **Features Used**:
  - Grid system (12-column layout)
  - Card components for panels
  - Button styles
  - Modal dialogs
  - Progress bars
  - Alerts and toasts
- **CDN Link**:
  ```html
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  ```

### **HTMX (Latest)**
- **Purpose**: Dynamic HTML content swapping without page reloads
- **Key Features**:
  - `hx-get`: Fetch and swap HTML from server
  - `hx-post`: Submit forms and get HTML response
  - `hx-trigger`: Event-based triggers
  - `hx-target`: Target element for swap
  - `hx-swap`: Swap strategy (innerHTML, outerHTML, etc.)
- **Use Cases**:
  - Start/stop pipeline steps
  - Real-time status updates
  - Form submissions
  - Progress tracking
- **CDN Link**:
  ```html
  <script src="https://unpkg.com/htmx.org@latest"></script>
  ```

### **Alpine.js (Latest)**
- **Purpose**: Lightweight reactivity for interactive components
- **Key Features**:
  - `x-data`: Component state
  - `x-show/x-if`: Conditional rendering
  - `x-on`: Event binding
  - `x-model`: Two-way data binding
  - `x-watch`: Reactive computed properties
- **Use Cases**:
  - Tab switching
  - Modal control
  - Form validation
  - Real-time UI state management
  - Countdown timers
- **CDN Link**:
  ```html
  <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
  ```

### **jQuery 3.7.1**
- **Purpose**: DOM manipulation (bundled with Bootstrap, optional)
- **Note**: Bootstrap 5.3+ doesn't require jQuery, but kept for compatibility
- **CDN Link** (optional):
  ```html
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  ```

---

## File Examples

### **Frontend - index.html**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Trading Quant Engine</title>

    <!-- Bootstrap 5.3 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link rel="stylesheet" href="css/style.css">
</head>
<body x-data="app()" @load="initApp()">
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">📈 Quant Trading Engine</span>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Pipeline Controls -->
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>Pipeline Control</h5>
                    </div>
                    <div class="card-body">
                        <!-- Step 1: Generate Features -->
                        <button
                            class="btn btn-outline-primary w-100 mb-2"
                            hx-post="/api/pipeline/features"
                            hx-target="#status"
                            @click="status='Running Features...'">
                            Step 1: Generate Features
                        </button>

                        <!-- Step 2: Generate Labels -->
                        <button
                            class="btn btn-outline-primary w-100 mb-2"
                            hx-post="/api/pipeline/labels"
                            hx-target="#status">
                            Step 2: Generate Labels
                        </button>

                        <!-- Step 3: Train Models -->
                        <button
                            class="btn btn-outline-primary w-100 mb-2"
                            hx-post="/api/pipeline/train"
                            hx-target="#status">
                            Step 3: Train Models
                        </button>

                        <!-- Step 4: Generate Predictions -->
                        <button
                            class="btn btn-outline-primary w-100 mb-2"
                            hx-post="/api/pipeline/score"
                            hx-target="#status">
                            Step 4: Generate Predictions
                        </button>

                        <!-- Step 5: Start API -->
                        <button
                            class="btn btn-success w-100"
                            hx-post="/api/pipeline/start-api"
                            hx-target="#status">
                            Step 5: Start API (port 8000)
                        </button>
                    </div>
                </div>
            </div>

            <!-- Status & Logs -->
            <div class="col-md-9">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5>Pipeline Status</h5>
                    </div>
                    <div class="card-body" id="status">
                        <div class="alert alert-info">
                            Ready to start. Click "Step 1" to begin.
                        </div>
                    </div>
                </div>

                <!-- Results -->
                <div class="card mt-3">
                    <div class="card-header bg-success text-white">
                        <h5>Results & Predictions</h5>
                    </div>
                    <div class="card-body" id="results">
                        <div class="alert alert-secondary">
                            Results will appear here after training completes.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@latest"></script>

    <!-- Alpine.js -->
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>

    <!-- App JS -->
    <script src="js/app.js"></script>
</body>
</html>
```

### **Frontend - js/app.js**
```javascript
function app() {
    return {
        status: 'Ready to start',
        isRunning: false,
        currentStep: null,

        async initApp() {
            console.log('App initialized');
            // Check if API is running
            this.checkApiStatus();
        },

        async checkApiStatus() {
            try {
                const response = await fetch('http://localhost:8000/v1/health');
                if (response.ok) {
                    this.status = '✅ API is running on port 8000';
                }
            } catch (e) {
                this.status = '⚠️ API not running';
            }
        },

        onHtmxSend() {
            this.isRunning = true;
        },

        onHtmxComplete() {
            this.isRunning = false;
            this.checkApiStatus();
        }
    }
}

// HTMX event listeners
document.addEventListener('htmx:sendRequest', () => {
    document.body.classList.add('cursor-wait');
});

document.addEventListener('htmx:afterRequest', () => {
    document.body.classList.remove('cursor-wait');
});
```

### **Backend - app.py (Control Server)**
```python
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import os

app = FastAPI(title="Quant Trading Control")

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open("frontend/index.html") as f:
        return f.read()

@app.post("/api/pipeline/features")
async def generate_features(background_tasks: BackgroundTasks):
    """Run feature generation"""
    background_tasks.add_task(
        subprocess.run,
        ["python", "etl/build_features.py", "--use-samples"],
        check=True
    )
    return {"status": "Features generation started..."}

@app.post("/api/pipeline/labels")
async def generate_labels(background_tasks: BackgroundTasks):
    """Run label generation"""
    background_tasks.add_task(
        subprocess.run,
        ["python", "labeling/make_labels.py", "--use-samples"],
        check=True
    )
    return {"status": "Label generation started..."}

@app.post("/api/pipeline/train")
async def train_models(background_tasks: BackgroundTasks):
    """Train models"""
    background_tasks.add_task(
        subprocess.run,
        ["python", "modeling/pipeline.py", "--train", "--use-samples"],
        check=True
    )
    return {"status": "Model training started..."}

@app.post("/api/pipeline/score")
async def generate_predictions(background_tasks: BackgroundTasks):
    """Generate predictions"""
    background_tasks.add_task(
        subprocess.run,
        ["python", "modeling/pipeline.py", "--score", "--use-samples"],
        check=True
    )
    return {"status": "Prediction generation started..."}

@app.post("/api/pipeline/start-api")
async def start_api(background_tasks: BackgroundTasks):
    """Start the prediction API"""
    background_tasks.add_task(
        subprocess.run,
        ["uvicorn", "api.main:app", "--reload", "--port", "8000"],
        check=True
    )
    return {"status": "API starting on port 8000..."}
```

---

## Setup Instructions

### **1. Install Python Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Install Control Server**
The control server (app.py) uses FastAPI (already in requirements.txt)

### **3. Run Control Server**
```bash
# Option A: FastAPI
uvicorn app:app --port 3000

# Option B: Flask (alternative)
python app.py
```

### **4. Access in Browser**
```
http://localhost:3000
```

---

## Technology Rationale

### **Why Bootstrap 5.3?**
- ✅ Latest version with modern components
- ✅ No jQuery dependency (though compatible)
- ✅ Excellent responsive design
- ✅ Large community and documentation
- ✅ Professional appearance out-of-the-box

### **Why HTMX?**
- ✅ No page reloads = smooth UX
- ✅ Server-renders HTML = less JS complexity
- ✅ Perfect for Hypermedia-driven apps
- ✅ Minimal learning curve
- ✅ Pairs perfectly with FastAPI

### **Why Alpine.js?**
- ✅ Lightweight (15KB) vs React/Vue (60KB+)
- ✅ Great for interactive components without compilation
- ✅ No virtual DOM = faster for simple interactions
- ✅ Perfect complement to HTMX
- ✅ Progressive enhancement friendly

### **Why FastAPI for Control Server?**
- ✅ Same codebase as existing API
- ✅ Built-in async support
- ✅ WebSocket support (future enhancements)
- ✅ Automatic API documentation
- ✅ Background task support

---

## Feature Development Roadmap

### **Phase 1: MVP (Immediate)**
- [ ] Dashboard with 5 pipeline buttons
- [ ] Basic status display
- [ ] HTMX real-time updates

### **Phase 2: Enhanced (Week 2)**
- [ ] WebSocket for live logs
- [ ] Progress bars for each step
- [ ] Error notifications (Bootstrap toasts)

### **Phase 3: Advanced (Week 3+)**
- [ ] Prediction results table
- [ ] Charts/visualizations (Chart.js)
- [ ] Model performance metrics
- [ ] Parameter tuning interface

---

## Key Development Tips

### **HTMX Best Practices**
```html
<!-- Use hx-swap for different strategies -->
<div hx-post="/endpoint"
     hx-target="#target"
     hx-swap="innerHTML swap:1s">
</div>

<!-- Use hx-trigger for custom events -->
<button hx-post="/api"
        hx-trigger="click, myEvent from:body">
</button>
```

### **Alpine.js Best Practices**
```javascript
// Use x-ref for element access
<input x-ref="myInput">
<button @click="$refs.myInput.focus()">Focus</button>

// Use x-watch for reactive updates
<div x-data="{ count: 0 }" x-watch="count">
```

### **Bootstrap Customization**
```css
/* Custom theme colors */
:root {
  --bs-primary: #0d6efd;
  --bs-success: #198754;
}
```

---

## Performance Considerations

| Metric | Target | Strategy |
|--------|--------|----------|
| Page Load | < 2s | Compress assets, use CDN |
| HTMX Swaps | < 500ms | Optimize server response |
| Alpine Updates | < 100ms | Minimize x-watch handlers |
| Total Bundle | < 1MB | Tree-shake unused Bootstrap |

---

## Accessibility & SEO

- ✅ Semantic HTML5 (`<main>`, `<nav>`, `<section>`)
- ✅ ARIA labels for interactive elements
- ✅ Keyboard navigation support (Bootstrap + Alpine)
- ✅ Color contrast compliance (WCAG AA)
- ✅ Meta tags for social sharing

---

## References

- [Bootstrap 5.3 Docs](https://getbootstrap.com/docs/5.3/)
- [HTMX Documentation](https://htmx.org/)
- [Alpine.js Documentation](https://alpinejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [jQuery 3.7.1 Docs](https://jquery.com/)

---

## Next Steps

1. Create `frontend/` directory structure
2. Write `app.py` control server
3. Create `index.html` dashboard
4. Implement HTMX endpoints
5. Add Alpine.js reactivity
6. Test with subprocess execution
7. Add WebSocket for real-time logs
8. Build advanced features (charts, metrics)

---

**Last Updated**: October 2025
**Version**: 1.0
**Status**: Ready for development
