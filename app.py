"""
Stock Trading Quant Engine - Control Server
FastAPI application for orchestrating the ML pipeline
Bootstrap 5.3 + HTMX + Alpine.js frontend
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
from pathlib import Path
import asyncio
import logging
from datetime import datetime

# ============================================
# Configuration
# ============================================

APP_TITLE = "Stock Trading Quant Engine"
APP_VERSION = "1.0.0"
CONTROL_PORT = 3000
ML_API_PORT = 8000
FRONTEND_DIR = "frontend"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# FastAPI App Initialization
# ============================================

app = FastAPI(
    title=APP_TITLE,
    description="Interactive ML Pipeline Control Dashboard",
    version=APP_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Static Files & Frontend
# ============================================

# Mount static files (CSS, JS, images)
if Path(FRONTEND_DIR).exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    logger.info(f"✅ Mounted static files from {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ Frontend directory not found: {FRONTEND_DIR}")

# ============================================
# Routes - HTML Pages
# ============================================

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard"""
    frontend_file = Path(FRONTEND_DIR) / "index.html"

    if not frontend_file.exists():
        return """
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>⚠️ Frontend Not Found</h1>
            <p>The frontend files are missing. Please ensure the <code>frontend/</code> directory exists.</p>
            <p>Expected file: <code>frontend/index.html</code></p>
        </body>
        </html>
        """

    with open(frontend_file, 'r') as f:
        return f.read()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": APP_TITLE,
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# Routes - Pipeline API
# ============================================

@app.post("/api/pipeline/features")
async def generate_features(background_tasks: BackgroundTasks):
    """
    Generate features from sample data
    Step 1 of the pipeline
    """
    logger.info("📊 Starting feature generation...")

    def run_features():
        try:
            logger.info("Running: python etl/build_features.py --use-samples")
            result = subprocess.run(
                ["python", "etl/build_features.py", "--use-samples"],
                capture_output=True,
                text=True,
                check=True,
                timeout=600  # 10 minutes
            )
            logger.info(f"✅ Features generated successfully\n{result.stdout}")
        except subprocess.TimeoutExpired:
            logger.error("❌ Feature generation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Feature generation failed: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")

    background_tasks.add_task(run_features)

    return {
        "step": 1,
        "status": "started",
        "message": "⚡ Feature generation started in background...",
        "details": "Processing 120 trading days with 46 engineered features"
    }

@app.post("/api/pipeline/labels")
async def generate_labels(background_tasks: BackgroundTasks):
    """
    Generate labels (20-day excess returns)
    Step 2 of the pipeline
    """
    logger.info("🏷️ Starting label generation...")

    def run_labels():
        try:
            logger.info("Running: python labeling/make_labels.py --use-samples")
            result = subprocess.run(
                ["python", "labeling/make_labels.py", "--use-samples"],
                capture_output=True,
                text=True,
                check=True,
                timeout=600
            )
            logger.info(f"✅ Labels generated successfully\n{result.stdout}")
        except subprocess.TimeoutExpired:
            logger.error("❌ Label generation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Label generation failed: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")

    background_tasks.add_task(run_labels)

    return {
        "step": 2,
        "status": "started",
        "message": "🏷️ Label generation started in background...",
        "details": "Computing 20-day excess returns vs KOSPI benchmark"
    }

@app.post("/api/pipeline/train")
async def train_models(background_tasks: BackgroundTasks):
    """
    Train HMM + Elastic Net models
    Step 3 of the pipeline
    """
    logger.info("Starting model training...")

    def run_training():
        try:
            logger.info("Running: python modeling/pipeline.py --train --use-samples")
            result = subprocess.run(
                ["python", "modeling/pipeline.py", "--train", "--use-samples"],
                capture_output=True,
                text=True,
                check=True,
                timeout=600
            )
            logger.info(f"✅ Training completed successfully\n{result.stdout}")
        except subprocess.TimeoutExpired:
            logger.error("❌ Training timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Training failed: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")

    background_tasks.add_task(run_training)

    return {
        "step": 3,
        "status": "started",
        "message": "Model training started in background...",
        "details": "Training HMM (regime detection) + Elastic Net classifier"
    }

@app.post("/api/pipeline/score")
async def generate_predictions(background_tasks: BackgroundTasks):
    """
    Generate predictions using trained models
    Step 4 of the pipeline
    """
    logger.info("🎯 Starting prediction generation...")

    def run_scoring():
        try:
            logger.info("Running: python modeling/pipeline.py --score --use-samples")
            result = subprocess.run(
                ["python", "modeling/pipeline.py", "--score", "--use-samples"],
                capture_output=True,
                text=True,
                check=True,
                timeout=600
            )
            logger.info(f"✅ Predictions generated successfully\n{result.stdout}")
        except subprocess.TimeoutExpired:
            logger.error("❌ Scoring timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Scoring failed: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")

    background_tasks.add_task(run_scoring)

    return {
        "step": 4,
        "status": "started",
        "message": "🎯 Prediction generation started in background...",
        "details": "Generating predictions for Samsung and SK Hynix"
    }

@app.post("/api/pipeline/start-api")
async def start_api(background_tasks: BackgroundTasks):
    """
    Start the ML prediction API server
    Step 5 of the pipeline
    """
    logger.info("🚀 Starting ML API server...")

    def run_api():
        try:
            logger.info(f"Running: uvicorn api.main:app --reload --port {ML_API_PORT}")
            result = subprocess.run(
                ["uvicorn", "api.main:app", "--reload", "--port", str(ML_API_PORT)],
                capture_output=True,
                text=True,
                check=True,
                timeout=None  # No timeout for long-running service
            )
            logger.info(f"API started: {result.stdout}")
        except subprocess.TimeoutExpired:
            logger.error("❌ API startup timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ API startup failed: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")

    background_tasks.add_task(run_api)

    return {
        "step": 5,
        "status": "started",
        "message": f"🚀 ML API server starting on port {ML_API_PORT}...",
        "details": f"Access the API at http://localhost:{ML_API_PORT}",
        "api_docs": f"http://localhost:{ML_API_PORT}/docs"
    }

# ============================================
# Routes - Status & Info
# ============================================

@app.get("/api/status")
async def pipeline_status():
    """Get current pipeline status"""
    return {
        "control_server": f"http://localhost:{CONTROL_PORT}",
        "ml_api_server": f"http://localhost:{ML_API_PORT}",
        "api_docs": f"http://localhost:{ML_API_PORT}/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/info")
async def app_info():
    """Get application information"""
    return {
        "title": APP_TITLE,
        "version": APP_VERSION,
        "frontend_framework": "Bootstrap 5.3 + HTMX + Alpine.js",
        "backend_framework": "FastAPI + Python",
        "ml_framework": "scikit-learn + hmmlearn",
        "description": "Interactive ML Pipeline Control Dashboard for Quantitative Trading"
    }

# ============================================
# Error Handlers
# ============================================

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle all exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "message": str(exc),
        "status": 500
    }

# ============================================
# Startup & Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("=" * 60)
    logger.info(f"🚀 {APP_TITLE} v{APP_VERSION}")
    logger.info("=" * 60)
    logger.info(f"📍 Control Server: http://localhost:{CONTROL_PORT}")
    logger.info(f"📍 ML API Server: http://localhost:{ML_API_PORT}")
    logger.info(f"📚 API Docs: http://localhost:{ML_API_PORT}/docs")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("=" * 60)
    logger.info("👋 Shutting down application")
    logger.info("=" * 60)

# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print(f"🚀 {APP_TITLE} v{APP_VERSION}")
    print("=" * 60)
    print(f"📍 Control Server: http://localhost:{CONTROL_PORT}")
    print(f"📍 ML API Server: http://localhost:{ML_API_PORT}")
    print(f"📚 API Docs: http://localhost:{ML_API_PORT}/docs")
    print("\n💡 Technologies:")
    print("   • Frontend: Bootstrap 5.3 + HTMX + Alpine.js")
    print("   • Backend: FastAPI + Python")
    print("   • ML: scikit-learn + hmmlearn")
    print("=" * 60 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=CONTROL_PORT,
        reload=True,
        log_level="info"
    )
