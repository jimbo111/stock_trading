"""FastAPI application for serving predictions."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import HealthResponse, Prediction, PredictionListResponse
from stores.prediction_store import PredictionStore
from utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Semis Alpha API",
    description="Korean semiconductor stock alpha predictions",
    version="0.1.0"
)

# Enable CORS for dashboard on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_config():
    """Load project configuration."""
    config_path = Path("config/default.yaml")
    if not config_path.exists():
        return {"paths": {"preds": "./data/preds"}}
    
    with open(config_path) as f:
        return yaml.safe_load(f)


config = load_config()
pred_store = PredictionStore(config['paths']['preds'])


@app.get("/v1/health", response_model=HealthResponse)
def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="0.1.0"
    )


@app.get("/v1/predict", response_model=Prediction)
def predict(
    symbol: str = Query(..., description="Stock symbol (e.g., '005930.KS')"),
    as_of_date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to latest")
):
    """Get prediction for a specific symbol and date.
    
    Args:
        symbol: Stock symbol
        as_of_date: Optional date, uses latest if not specified
        
    Returns:
        Prediction object
    """
    try:
        if as_of_date:
            predictions = pred_store.read_json(as_of_date)
        else:
            predictions = pred_store.latest_json()
            
        # Find matching symbol
        for pred in predictions:
            if pred['symbol'] == symbol:
                return Prediction(**pred)
        
        raise HTTPException(
            status_code=404,
            detail=f"No prediction found for symbol {symbol}"
        )
    
    except FileNotFoundError as e:
        logger.error(f"Predictions not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Predictions not found for specified date"
        )
    except Exception as e:
        logger.error(f"Error retrieving prediction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/v1/predictions", response_model=PredictionListResponse)
def list_predictions(
    as_of_date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to latest")
):
    """Get all predictions for a specific date.
    
    Args:
        as_of_date: Optional date, uses latest if not specified
        
    Returns:
        List of predictions
    """
    try:
        if as_of_date:
            predictions = pred_store.read_json(as_of_date)
        else:
            predictions = pred_store.latest_json()
            as_of_date = predictions[0]['as_of_date'] if predictions else "unknown"
        
        return PredictionListResponse(
            predictions=[Prediction(**p) for p in predictions],
            count=len(predictions),
            as_of_date=as_of_date
        )
    
    except FileNotFoundError as e:
        logger.error(f"Predictions not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="No predictions available"
        )
    except Exception as e:
        logger.error(f"Error retrieving predictions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/v1/dates", response_model=List[str])
def list_dates():
    """List all available prediction dates.
    
    Returns:
        List of date strings
    """
    try:
        return pred_store.list_dates()
    except Exception as e:
        logger.error(f"Error listing dates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
