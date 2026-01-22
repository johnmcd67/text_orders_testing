"""
Database connection and CRUD operations for job_runs table
Uses psycopg v3 for PostgreSQL operations
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")


def get_db_connection():
    """Create psycopg3 connection from DATABASE_URL env var"""
    return psycopg.connect(DATABASE_URL)


def create_job() -> int:
    """
    Insert new job with status='pending', return job_id

    Returns:
        int: The ID of the newly created job
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO public.job_runs (status, progress)
            VALUES ('pending', 0)
            RETURNING id
        """)
        job_id = cursor.fetchone()[0]
        conn.commit()
        return job_id
    finally:
        cursor.close()
        conn.close()


def get_job_status(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Query job_runs by id, return dict with all fields

    Args:
        job_id: The ID of the job to query

    Returns:
        dict: Job data with keys: id, status, progress, progress_message, created_at, completed_at
        None if job not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, status, progress, progress_message, created_at, completed_at
            FROM public.job_runs
            WHERE id = %s
        """, (job_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "status": row[1],
            "progress": row[2],
            "progress_message": row[3],
            "created_at": row[4],
            "completed_at": row[5]
        }
    finally:
        cursor.close()
        conn.close()


def update_job_status(job_id: int, status: str):
    """
    Update job status

    Args:
        job_id: The ID of the job to update
        status: New status value (pending, running, awaiting_review, completed, failed)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET status = %s
            WHERE id = %s
        """, (status, job_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_job_progress(job_id: int, progress: int):
    """
    Update job progress (0-100 or count of PDFs processed)

    Args:
        job_id: The ID of the job to update
        progress: Progress value (typically 0-100)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET progress = %s
            WHERE id = %s
        """, (progress, job_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_job_progress_message(job_id: int, message: str):
    """
    Update job progress message (detailed status for user)

    Args:
        job_id: The ID of the job to update
        message: Progress message (e.g., "Processing email 23/50... Running subagent: SKU extraction")
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET progress_message = %s
            WHERE id = %s
        """, (message, job_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_job_progress_with_message(job_id: int, progress: int, message: str):
    """
    Update both progress percentage and message in single call

    Args:
        job_id: The ID of the job to update
        progress: Progress value (typically 0-100)
        message: Progress message for user
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET progress = %s,
                progress_message = %s
            WHERE id = %s
        """, (progress, message, job_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def complete_job(job_id: int):
    """
    Set status='completed', completed_at=NOW()

    Args:
        job_id: The ID of the job to complete
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                progress = 100
            WHERE id = %s
        """, (job_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def fail_job(job_id: int, error_message: str = None):
    """
    Set status='failed' and mark job as completed

    Args:
        job_id: The ID of the job that failed
        error_message: Description of the error (logged but not stored in DB)
    """
    if error_message:
        print(f"[Database] Job {job_id} failed: {error_message}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE public.job_runs
            SET status = 'failed',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (job_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

