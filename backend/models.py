"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint"""
    id: int
    status: str  # pending, running, awaiting_review_data, completed, failed
    progress: Optional[int] = None
    progress_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class JobCreateResponse(BaseModel):
    """Response model for job creation endpoint"""
    job_id: int
    status: str
    message: str


class JobPreviewResponse(BaseModel):
    """Response model for job preview endpoint"""
    job_id: int
    data: List[Dict[str, Any]]  # CSV data as JSON array


class JobApproveRequest(BaseModel):
    """Request model for job approval endpoint"""
    approved: bool = True  # Future: could have reject reason
    orders: Optional[List[Dict[str, Any]]] = None  # Optional edited orders data


class JobApproveResponse(BaseModel):
    """Response model for job approval endpoint"""
    status: str
    message: str


class FailureSummaryResponse(BaseModel):
    """Response model for failure summary endpoint"""
    job_id: int
    has_failures: bool
    failure_count: int
    summary: Optional[str] = None
    generated_at: Optional[datetime] = None
    is_cached: bool = False

