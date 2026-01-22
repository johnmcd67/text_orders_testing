"""
Azure Blob Storage Helper
Provides unified file I/O that works with both local temp/ directory and Azure Blob Storage.
Automatically uses Azure if AZURE_STORAGE_CONNECTION_STRING is set, otherwise falls back to local.
"""
import os
import json
import shutil
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# Check if Azure Blob Storage is configured
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
USE_AZURE = bool(AZURE_STORAGE_CONNECTION_STRING)
CONTAINER_NAME = "text-order-processing-temp"

# Local temp directory path
LOCAL_TEMP_DIR = Path("temp")


def _get_blob_container():
    """Get Azure Blob container client (lazy import to avoid errors when not using Azure)."""
    from azure.storage.blob import BlobServiceClient
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container = blob_service.get_container_client(CONTAINER_NAME)
    # Create container if it doesn't exist
    try:
        container.create_container()
    except Exception:
        pass  # Container already exists
    return container


def _get_blob_name(filename: str, job_id: Optional[int] = None) -> str:
    """Generate blob name with optional job_id prefix."""
    if job_id:
        return f"job_{job_id}/{filename}"
    return filename


def _get_local_path(filename: str, job_id: Optional[int] = None) -> Path:
    """Generate local file path with optional job_id prefix."""
    if job_id:
        return LOCAL_TEMP_DIR / f"job_{job_id}" / filename
    return LOCAL_TEMP_DIR / filename


def ensure_temp_dir(job_id: Optional[int] = None) -> Path:
    """
    Ensure temp directory exists (for local storage).
    Returns the temp directory path.
    """
    if job_id:
        temp_path = LOCAL_TEMP_DIR / f"job_{job_id}"
    else:
        temp_path = LOCAL_TEMP_DIR
    temp_path.mkdir(parents=True, exist_ok=True)
    return temp_path


def cleanup_temp_dir():
    """Clean up the contents of the temp directory (local storage only)."""
    if LOCAL_TEMP_DIR.exists():
        # Delete contents instead of the directory itself to avoid Windows permission errors
        for item in LOCAL_TEMP_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except PermissionError:
                print(f"Warning: Could not delete {item} - skipping")
    else:
        LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data: Any, filename: str, job_id: Optional[int] = None) -> str:
    """
    Save JSON data to storage (Azure Blob or local).

    Args:
        data: Data to serialize as JSON
        filename: Name of the file (e.g., 'emails_raw.json')
        job_id: Optional job ID for organizing files

    Returns:
        Storage path/URL of saved file
    """
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    if USE_AZURE:
        container = _get_blob_container()
        blob_name = _get_blob_name(filename, job_id)
        container.upload_blob(blob_name, json_content, overwrite=True)
        return f"blob://{CONTAINER_NAME}/{blob_name}"
    else:
        local_path = _get_local_path(filename, job_id)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        return str(local_path)


def load_json(filename: str, job_id: Optional[int] = None) -> Any:
    """
    Load JSON data from storage (Azure Blob or local).

    Args:
        filename: Name of the file (e.g., 'emails_raw.json')
        job_id: Optional job ID for organizing files

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if USE_AZURE:
        container = _get_blob_container()
        blob_name = _get_blob_name(filename, job_id)
        try:
            blob_data = container.download_blob(blob_name)
            return json.loads(blob_data.readall().decode('utf-8'))
        except Exception as e:
            raise FileNotFoundError(f"Blob not found: {blob_name}") from e
    else:
        local_path = _get_local_path(filename, job_id)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)


def save_csv(df: pd.DataFrame, filename: str, job_id: Optional[int] = None) -> str:
    """
    Save DataFrame to CSV in storage (Azure Blob or local).

    Args:
        df: Pandas DataFrame to save
        filename: Name of the file (e.g., 'order_details.csv')
        job_id: Optional job ID for organizing files

    Returns:
        Storage path/URL of saved file
    """
    csv_content = df.to_csv(index=False, encoding='utf-8')

    if USE_AZURE:
        container = _get_blob_container()
        blob_name = _get_blob_name(filename, job_id)
        container.upload_blob(blob_name, csv_content, overwrite=True)
        return f"blob://{CONTAINER_NAME}/{blob_name}"
    else:
        local_path = _get_local_path(filename, job_id)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)
        return str(local_path)


def load_csv(filename: str, job_id: Optional[int] = None) -> pd.DataFrame:
    """
    Load CSV from storage as DataFrame (Azure Blob or local).

    Args:
        filename: Name of the file (e.g., 'order_details.csv')
        job_id: Optional job ID for organizing files

    Returns:
        Pandas DataFrame

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if USE_AZURE:
        from io import StringIO
        container = _get_blob_container()
        blob_name = _get_blob_name(filename, job_id)
        try:
            blob_data = container.download_blob(blob_name)
            csv_content = blob_data.readall().decode('utf-8')
            return pd.read_csv(StringIO(csv_content))
        except Exception as e:
            raise FileNotFoundError(f"Blob not found: {blob_name}") from e
    else:
        local_path = _get_local_path(filename, job_id)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        return pd.read_csv(local_path)


def cleanup_job_files(job_id: int):
    """
    Delete all files for a specific job.

    Args:
        job_id: Job ID to clean up
    """
    if USE_AZURE:
        container = _get_blob_container()
        prefix = f"job_{job_id}/"
        blobs = container.list_blobs(name_starts_with=prefix)
        for blob in blobs:
            container.delete_blob(blob.name)
    else:
        job_dir = LOCAL_TEMP_DIR / f"job_{job_id}"
        if job_dir.exists():
            shutil.rmtree(job_dir)


def file_exists(filename: str, job_id: Optional[int] = None) -> bool:
    """
    Check if a file exists in storage.

    Args:
        filename: Name of the file
        job_id: Optional job ID

    Returns:
        True if file exists, False otherwise
    """
    if USE_AZURE:
        container = _get_blob_container()
        blob_name = _get_blob_name(filename, job_id)
        return container.get_blob_client(blob_name).exists()
    else:
        local_path = _get_local_path(filename, job_id)
        return local_path.exists()


# For backward compatibility - these work with the existing temp/ structure
def get_temp_path(filename: str = "") -> Path:
    """Get path to temp directory or file within it (local only)."""
    ensure_temp_dir()
    if filename:
        return LOCAL_TEMP_DIR / filename
    return LOCAL_TEMP_DIR
