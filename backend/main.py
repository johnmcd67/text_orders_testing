"""
FastAPI Backend for Text Order Processing Web Application
Complete workflow with 4 tasks and review pause point
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from celery import chain
import os

from backend.models import (
    JobStatusResponse,
    JobCreateResponse,
    JobPreviewResponse,
    JobApproveRequest,
    JobApproveResponse,
    FailureSummaryResponse
)
from datetime import datetime
from backend.database import (
    create_job,
    get_job_status,
    update_job_status
)
from backend.utils.database import get_db_helper
from backend.utils.blob_storage import load_csv, save_csv, file_exists

# Import all tasks
from backend.tasks.task_fetch_emails import fetch_emails_task
from backend.tasks.task_extract_emails import extract_emails_task
from backend.tasks.task_extract_data import extract_data_task
from backend.tasks.task_tidy_emails import tidy_emails_task

# Import auth router
from backend.routes.auth import router as auth_router

# Initialize FastAPI app
app = FastAPI(
    title="Text Order Processing API",
    description="Backend API for text order processing with email extraction, data extraction, and email management",
    version="1.0.0"
)

# Configure CORS for React frontend
# Build allowed origins list from environment variable + defaults
cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Fallback dev port
]

# Add production frontend URL from environment variable
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth router
app.include_router(auth_router)


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Text Order Processing API",
        "version": "1.0.0",
        "workflow": "Fetch Emails → Extract Emails → Extract Data → [Review Data] → Tidy Emails"
    }


@app.post("/api/jobs/start", response_model=JobCreateResponse)
def start_job():
    """
    Start a new text order processing job

    Workflow:
    1. Create job record in database (status='pending')
    2. Chain Task 1 (Fetch Emails) → Task 2 (Extract Emails) → Task 3 (Extract Data)
    3. Pause at status='awaiting_review_data' for user to review extracted orders
    4. User approves → Task 4 (Tidy Emails) runs
    5. Complete

    Returns:
        JobCreateResponse: Job ID and initial status
    """
    try:
        # Create job in database
        job_id = create_job()

        # Chain Task 1 (Fetch Emails) → Task 2 (Extract Emails)
        # Task 2 auto-chains to Task 3 (Extract Data)
        # Task 4 is triggered manually after user approval
        workflow = chain(
            fetch_emails_task.s(job_id),
            extract_emails_task.si(job_id)  # .si() = immutable signature, auto-chains to Task 3
        )

        workflow.apply_async()

        return JobCreateResponse(
            job_id=job_id,
            status="pending",
            message="Job created successfully. Email fetching, extraction, and data processing started."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@app.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_status(job_id: int):
    """
    Get current status of a job

    Args:
        job_id: ID of the job to query

    Returns:
        JobStatusResponse: Current job status, progress, progress_message, and timestamps
    """
    try:
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return JobStatusResponse(**job_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@app.get("/api/jobs/{job_id}/preview", response_model=JobPreviewResponse)
def get_preview(job_id: int):
    """
    Get preview of extracted data for review (Pause Point)

    This endpoint is called when job status = 'awaiting_review_data'
    User reviews extracted orders (structured data) before emails are tidied

    Args:
        job_id: ID of the job to preview

    Returns:
        JobPreviewResponse: Extracted order data from order_details.csv
    """
    try:
        # Verify job exists and is in correct status
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Check if job is awaiting data review
        if job_data["status"] != "awaiting_review_data":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not awaiting data review. Current status: {job_data['status']}"
            )

        # Read order_details.csv from storage (Azure Blob or local)
        if not file_exists('order_details.csv'):
            raise HTTPException(
                status_code=404,
                detail=f"Order details not found for job {job_id}"
            )

        # Read CSV from storage and convert to list of dicts
        df = load_csv('order_details.csv')
        data = df.to_dict(orient='records')

        return JobPreviewResponse(
            job_id=job_id,
            data=data
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data preview: {str(e)}")


@app.post("/api/jobs/{job_id}/approve", response_model=JobApproveResponse)
def approve_job(job_id: int, request: JobApproveRequest):
    """
    Approve extracted data and continue to email tidying (Resume from Pause Point)

    Args:
        job_id: ID of the job to approve
        request: Approval request (approved=True)

    Returns:
        JobApproveResponse: Status and message
    """
    try:
        # Verify job exists
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Verify job is awaiting data review
        if job_data["status"] != "awaiting_review_data":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not awaiting data review. Current status: {job_data['status']}"
            )

        if request.approved:
            # If edited orders are provided, write them to CSV
            if request.orders:
                try:
                    # Write edited orders to storage (Azure Blob or local)
                    df_output = pd.DataFrame(request.orders)

                    # Ensure columns match expected structure
                    output_columns = [
                        "orderno", "customerid", "customer_name", "sku", "quantity",
                        "reference_no", "valve", "delivery_address", "cpsd", "entry_id",
                        "option_sku", "option_qty", "telephone_number", "contact_name"
                    ]

                    # Add missing columns with None if they don't exist
                    for col in output_columns:
                        if col not in df_output.columns:
                            df_output[col] = None

                    # Select only the expected columns
                    df_output = df_output[output_columns]
                    save_csv(df_output, 'order_details.csv')
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to write edited orders to CSV: {str(e)}"
                    )
            
            # Update status to running immediately so frontend polling resumes
            update_job_status(job_id, "running")

            # Trigger Task 4 (Email Tidying)
            tidy_emails_task.delay(job_id)

            return JobApproveResponse(
                status="approved",
                message="Data approved. Email tidying started."
            )
        else:
            # User rejected data
            update_job_status(job_id, "failed")
            return JobApproveResponse(
                status="rejected",
                message="Extracted data rejected by user. Job marked as failed."
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve job: {str(e)}")


@app.get("/api/jobs/{job_id}/results")
def get_results(job_id: int, file_type: str = "order_details"):
    """
    Download final results as CSV file

    Args:
        job_id: ID of the job to download results for
        file_type: Type of file to download ('order_details' or 'failed_orders')

    Returns:
        FileResponse: CSV file download
    """
    try:
        # Verify job exists and is completed
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job_data["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed. Current status: {job_data['status']}"
            )

        # Determine which file to return
        if file_type == "order_details":
            # Query database on-demand for Clavei Input CSV
            try:
                db_helper = get_db_helper()
                column_names, rows = db_helper.get_clavei_input_data()

                # Convert to DataFrame and save as CSV
                df = pd.DataFrame(rows, columns=column_names)
                results_path = Path("temp/clavei_input.csv")
                df.to_csv(results_path, index=False, encoding='utf-8')
                filename = f"job_{job_id}_clavei_input.csv"
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate Clavei Input CSV: {str(e)}"
                )
        elif file_type == "failed_orders":
            filename = f"job_{job_id}_failed_orders.csv"

            # Check if failed_orders.csv exists in storage (it's only created if there are failures)
            if not file_exists('failed_orders.csv'):
                raise HTTPException(
                    status_code=404,
                    detail=f"No failed orders for job {job_id}"
                )

            # Download from storage to local temp for FileResponse
            df_failed = load_csv('failed_orders.csv')
            results_path = Path("temp/failed_orders.csv")
            results_path.parent.mkdir(parents=True, exist_ok=True)
            df_failed.to_csv(results_path, index=False, encoding='utf-8')
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file_type: {file_type}. Must be 'order_details' or 'failed_orders'"
            )

        return FileResponse(
            path=str(results_path),
            filename=filename,
            media_type="text/csv"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@app.get("/api/jobs/{job_id}/failure-summary", response_model=FailureSummaryResponse)
def get_failure_summary(job_id: int, regenerate: bool = False):
    """
    Get or generate AI-powered summary of failed orders

    This endpoint retrieves failure context from the database and generates
    a human-readable summary using the Anthropic API. Summaries are cached
    per job_id.

    Args:
        job_id: ID of the job to get failure summary for
        regenerate: If True, regenerate even if cached summary exists

    Returns:
        FailureSummaryResponse: Summary and metadata
    """
    try:
        # Verify job exists
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Get failure contexts from database
        db_helper = get_db_helper()
        failure_contexts = db_helper.get_failure_context(job_id)

        # If no failures, return early
        if not failure_contexts:
            return FailureSummaryResponse(
                job_id=job_id,
                has_failures=False,
                failure_count=0,
                summary=None,
                generated_at=None,
                is_cached=False
            )

        failure_count = len(failure_contexts)

        # Check for cached summary (if not regenerating)
        if not regenerate:
            cached = db_helper.get_failure_summary(job_id)
            if cached and cached.get("failure_summary"):
                return FailureSummaryResponse(
                    job_id=job_id,
                    has_failures=True,
                    failure_count=failure_count,
                    summary=cached["failure_summary"],
                    generated_at=cached["failure_summary_generated_at"],
                    is_cached=True
                )

        # Generate new summary using Anthropic API
        summary = _generate_failure_summary(job_id, failure_contexts)

        # Cache the summary
        db_helper.save_failure_summary(job_id, summary)

        return FailureSummaryResponse(
            job_id=job_id,
            has_failures=True,
            failure_count=failure_count,
            summary=summary,
            generated_at=datetime.utcnow(),
            is_cached=False
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get failure summary: {str(e)}")


@app.get("/api/jobs/{job_id}/failure-summary/pdf")
def get_failure_summary_pdf(job_id: int):
    """
    Export failure summary as PDF document

    This endpoint generates a professionally formatted PDF from the failure summary.
    Uses the cached summary if available, otherwise generates a new one.

    Args:
        job_id: ID of the job to export failure summary for

    Returns:
        FileResponse: PDF file download
    """
    try:
        from backend.utils.pdf_generator import generate_failure_summary_pdf

        # Verify job exists
        job_data = get_job_status(job_id)

        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Get failure contexts from database
        db_helper = get_db_helper()
        failure_contexts = db_helper.get_failure_context(job_id)

        # If no failures, return error
        if not failure_contexts:
            raise HTTPException(
                status_code=404,
                detail=f"No failures to export for job {job_id}"
            )

        failure_count = len(failure_contexts)

        # Check for cached summary first
        cached = db_helper.get_failure_summary(job_id)
        if cached and cached.get("failure_summary"):
            summary = cached["failure_summary"]
            generated_at = cached.get("failure_summary_generated_at")
        else:
            # Generate new summary
            summary = _generate_failure_summary(job_id, failure_contexts)
            db_helper.save_failure_summary(job_id, summary)
            generated_at = datetime.utcnow()

        # Generate PDF
        pdf_bytes = generate_failure_summary_pdf(
            job_id=job_id,
            failure_count=failure_count,
            summary=summary,
            generated_at=generated_at
        )

        # Write to temp file for FileResponse
        temp_path = Path("temp") / f"failure_summary_job_{job_id}.pdf"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(pdf_bytes)

        return FileResponse(
            path=str(temp_path),
            filename=f"job_{job_id}_failure_summary.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to export failure summary PDF: {str(e)}")


def _generate_failure_summary(job_id: int, failure_contexts: List[Dict[str, Any]]) -> str:
    """
    Generate failure summary using Anthropic API

    Args:
        job_id: Job ID for context
        failure_contexts: List of failure context dictionaries

    Returns:
        str: AI-generated summary in markdown format
    """
    from backend.utils.anthropic_helper import get_anthropic_helper

    # Load prompt template
    prompt_template_path = Path("backend/prompts/failure_summary.txt")
    prompt_template = prompt_template_path.read_text(encoding='utf-8')

    # Format failure details for the prompt
    failure_details = _format_failure_details(failure_contexts)

    # Calculate statistics
    total_orders = len(set(fc.get("order_number") for fc in failure_contexts))
    failed_orders = total_orders  # All contexts represent failures

    # Build prompt
    prompt = prompt_template.format(
        job_id=job_id,
        total_orders=total_orders,
        successful_orders=0,  # All contexts are failures
        failed_orders=failed_orders,
        failure_details=failure_details
    )

    # Call Anthropic API
    anthropic_helper = get_anthropic_helper()
    response = anthropic_helper.call_with_retry(
        prompt=prompt,
        response_format="text",
        max_tokens=2000,
        timeout=180  # Extended timeout for failure summary (default is 30s)
    )

    # Extract text content from response dict
    return response.get("content", "")


def _format_failure_details(failure_contexts: List[Dict[str, Any]]) -> str:
    """
    Format failure contexts into readable text for the prompt

    Args:
        failure_contexts: List of failure context dictionaries

    Returns:
        str: Formatted failure details
    """
    lines = []

    for idx, fc in enumerate(failure_contexts, 1):
        failure_type = fc.get("type", "unknown")
        order_number = fc.get("order_number", "N/A")

        lines.append(f"\n### Failure {idx}: Order {order_number}")
        lines.append(f"**Type:** {failure_type}")

        if failure_type == "customer_id":
            lines.append(f"**Extracted Names:** {fc.get('extracted_names', [])}")
            lines.append(f"**Best Match Score:** {fc.get('best_match_score', 0):.2%}")
            lines.append(f"**Threshold Required:** {fc.get('threshold_used', 0.85):.0%}")
            lines.append(f"**Closest Match:** {fc.get('best_match_name', 'None')} (ID: {fc.get('best_match_id', 'N/A')})")
            if fc.get("email_snippet"):
                lines.append(f"**Email Preview:** {fc.get('email_snippet', '')[:200]}...")

        elif failure_type == "sku_extraction":
            reason = fc.get("reason", "unknown")
            lines.append(f"**Reason:** {reason}")

            if reason == "all_lines_failed":
                failed_lines = fc.get("failed_lines", [])
                for fl in failed_lines[:3]:  # Show first 3 failed lines
                    lines.append(f"\n  - **Line {fl.get('line_number', 'N/A')}:** {fl.get('reason', 'unknown')}")
                    if fl.get("extracted_family"):
                        lines.append(f"    Family: '{fl.get('extracted_family')}' (score: {fl.get('family_match_score', 0):.2%}, closest: '{fl.get('closest_family', 'N/A')}')")
                    if fl.get("extracted_color"):
                        lines.append(f"    Color: '{fl.get('extracted_color')}' (score: {fl.get('color_match_score', 0):.2%}, closest: '{fl.get('closest_color', 'N/A')}')")

            if fc.get("email_snippet"):
                lines.append(f"**Email Preview:** {fc.get('email_snippet', '')[:200]}...")

        elif failure_type == "exception":
            lines.append(f"**Exception:** {fc.get('exception_message', 'Unknown error')}")

    return "\n".join(lines)


# Additional utility endpoints

@app.get("/api/prompts/{prompt_name}")
def get_prompt(prompt_name: str):
    """
    Get prompt file content by name

    Args:
        prompt_name: Name of the prompt file (e.g., 'customer_id.txt')

    Returns:
        dict: Prompt file content
    """
    try:
        prompts_dir = Path("backend/prompts")
        prompt_path = prompts_dir / prompt_name

        if not prompt_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Prompt file '{prompt_name}' not found"
            )

        if not prompt_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"'{prompt_name}' is not a valid file"
            )

        content = prompt_path.read_text(encoding='utf-8')

        return {
            "filename": prompt_name,
            "content": content
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read prompt file: {str(e)}"
        )


@app.get("/api/jobs/history")
def get_job_history():
    """
    Get daily history of completed jobs

    Returns:
        list: List of dicts with date and count of completed jobs
    """
    try:
        from backend.database import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = '''
                SELECT CAST(completed_at as date) as date, COUNT(id) as count
                FROM public.job_runs
                WHERE status = 'completed'
                GROUP BY CAST(completed_at as date)
                ORDER BY CAST(completed_at as date)
            '''
            cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description]

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dicts
            result = []
            for row in rows:
                result.append({
                    "date": str(row[0]),  # Convert date to string for JSON serialization
                    "count": row[1]
                })

            return result
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job history: {str(e)}")


@app.get("/api/jobs/history/orders")
def get_orders_history():
    """
    Get daily history of completed orders

    Returns:
        list: List of dicts with date and total_orders
    """
    try:
        from backend.database import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = '''
                SELECT CAST(completed_at as date) AS date,
                       SUM(number_of_orders) AS total_orders
                FROM public.job_runs
                WHERE status = 'completed'
                AND number_of_orders IS NOT NULL
                GROUP BY CAST(completed_at as date)
                ORDER BY CAST(completed_at as date)
            '''
            cursor.execute(query)

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dicts
            result = []
            for row in rows:
                result.append({
                    "date": str(row[0]),  # Convert date to string for JSON serialization
                    "total_orders": row[1]
                })

            return result
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders history: {str(e)}")


@app.get("/api/jobs/history/order-lines")
def get_order_lines_history():
    """
    Get daily history of completed order lines

    Returns:
        list: List of dicts with date and total_order_lines
    """
    try:
        from backend.database import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = '''
                SELECT CAST(completed_at as date) AS date,
                       SUM(number_of_order_lines) AS total_order_lines
                FROM public.job_runs
                WHERE status = 'completed'
                AND number_of_order_lines IS NOT NULL
                GROUP BY CAST(completed_at as date)
                ORDER BY CAST(completed_at as date)
            '''
            cursor.execute(query)

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dicts
            result = []
            for row in rows:
                result.append({
                    "date": str(row[0]),  # Convert date to string for JSON serialization
                    "total_order_lines": row[1]
                })

            return result
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order lines history: {str(e)}")


@app.get("/api/jobs/history/avg-process-time")
def get_avg_process_time():
    """
    Get average process time per job

    Returns:
        list: List of dicts with date, job_id, and duration_seconds
    """
    try:
        from backend.database import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = '''
                SELECT CAST(completed_at as date),job_id,duration_seconds
                FROM
                (
                SELECT
                    id job_id,
                    status,
                    created_at,
                    completed_at,
                    number_of_order_lines,
                    (EXTRACT(EPOCH FROM (completed_at - created_at)) / number_of_order_lines) AS duration_seconds
                FROM public.job_runs
                WHERE status = 'completed'
                AND number_of_order_lines > 0
                ) tot
                GROUP BY CAST(completed_at as date),job_id,duration_seconds
                ORDER BY CAST(completed_at as date)
            '''
            cursor.execute(query)

            # Fetch all rows
            rows = cursor.fetchall()

            # Convert to list of dicts
            result = []
            for row in rows:
                result.append({
                    "date": str(row[0]),  # Convert date to string for JSON serialization
                    "job_id": row[1],
                    "duration_seconds": float(row[2]) if row[2] is not None else None
                })

            return result
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch average process time: {str(e)}")


@app.get("/api/health")
def health_check():
    """
    Comprehensive health check for container orchestration

    Returns:
        dict: Status of API and all dependencies
    """
    import os

    status = {
        "status": "healthy",
        "api": "online",
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown"
    }

    # Check database connection
    try:
        from backend.database import get_db_connection
        conn = get_db_connection()
        conn.close()
        status["database"] = "connected"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Redis/Celery
    try:
        from backend.celery_app import celery_app
        inspect = celery_app.control.inspect()
        workers = inspect.ping()  # Returns workers that respond (not active tasks)
        if workers:
            status["redis"] = "connected"
            status["celery"] = f"{len(workers)} worker(s) active"
        else:
            status["redis"] = "connected"
            status["celery"] = "no workers"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
        status["celery"] = "unavailable"
        status["status"] = "degraded"

    # Check Azure Blob Storage (if configured)
    azure_storage = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if azure_storage:
        try:
            from backend.utils.blob_storage import ensure_temp_dir
            ensure_temp_dir()
            status["blob_storage"] = "connected"
        except Exception as e:
            status["blob_storage"] = f"error: {str(e)}"

    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

