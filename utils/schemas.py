"""Pydantic schemas for API I/O."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Prediction(BaseModel):
    """Model prediction for a symbol on a specific date."""
    
    symbol: str = Field(..., description="Stock symbol (e.g., '005930.KS')")
    as_of_date: str = Field(..., description="Prediction date (YYYY-MM-DD)")
    p_up: float = Field(..., description="Probability of positive excess return", ge=0.0, le=1.0)
    er20_hat_bps: Optional[float] = Field(None, description="Expected 20D excess return in bps")
    state_probs: List[float] = Field(default_factory=list, description="HMM state probabilities")
    vol20_ann: Optional[float] = Field(None, description="20-day realized volatility (annualized)")
    weight_suggested: Optional[float] = Field(None, description="Suggested portfolio weight")
    model_version: str = Field(..., description="Model version identifier")
    degraded: bool = Field(False, description="Whether prediction is stale/degraded")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: Optional[str] = Field(None, description="API version")


class PredictionListResponse(BaseModel):
    """Response containing multiple predictions."""
    
    predictions: List[Prediction]
    count: int = Field(..., description="Number of predictions")
    as_of_date: str = Field(..., description="Date of predictions")
