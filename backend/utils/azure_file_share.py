"""
Azure File Share helper for uploading email files.

This module provides functions to upload email files (.eml) to Azure File Share,
making them instantly accessible to local users via mapped network drive.
"""

import os
from datetime import datetime
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from azure.core.exceptions import ResourceExistsError


def get_connection_string() -> str:
    """Build connection string from environment variables."""
    account_name = os.getenv('AZURE_STORAGE_ACCOUNT')
    account_key = os.getenv('AZURE_STORAGE_KEY')

    if not account_name or not account_key:
        raise ValueError(
            "Azure File Share credentials not configured. "
            "Set AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY environment variables."
        )

    return f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"


def ensure_date_folder_exists(share_name: str) -> str:
    """
    Create date folder structure (YYMMDD/YYMMDDAI) if it doesn't exist.

    Args:
        share_name: Name of the Azure File Share

    Returns:
        str: The date folder path (e.g., '251212/251212AI')
    """
    connection_string = get_connection_string()
    date_str = datetime.now().strftime("%y%m%d")
    parent_folder = date_str
    ai_folder = f"{date_str}AI"
    full_folder_path = f"{parent_folder}/{ai_folder}"

    # Create parent folder (YYMMDD)
    parent_client = ShareDirectoryClient.from_connection_string(
        connection_string, share_name, parent_folder
    )
    try:
        parent_client.create_directory()
        print(f"[Azure File Share] Created folder: {parent_folder}")
    except ResourceExistsError:
        pass

    # Create AI subfolder (YYMMDDAI)
    ai_client = ShareDirectoryClient.from_connection_string(
        connection_string, share_name, full_folder_path
    )
    try:
        ai_client.create_directory()
        print(f"[Azure File Share] Created folder: {full_folder_path}")
    except ResourceExistsError:
        pass

    return full_folder_path


def upload_email_file(file_content: bytes, filename: str, prefix: str = "TEXT") -> str:
    """
    Upload email file to Azure File Share.

    Args:
        file_content: Email content as bytes (.eml format)
        filename: Base name for the file (will be prefixed)
        prefix: "TEXT" or "PDF" to identify source app

    Returns:
        str: Full path to the uploaded file in Azure File Share
    """
    connection_string = get_connection_string()
    share_name = os.getenv('AZURE_FILE_SHARE')

    if not share_name:
        raise ValueError(
            "Azure File Share not configured. "
            "Set AZURE_FILE_SHARE environment variable."
        )

    # Ensure date folder exists
    folder_path = ensure_date_folder_exists(share_name)

    # Add prefix to filename
    prefixed_filename = f"{prefix}_{filename}"
    file_path = f"{folder_path}/{prefixed_filename}"

    # Upload file
    file_client = ShareFileClient.from_connection_string(
        connection_string, share_name, file_path
    )
    file_client.upload_file(file_content)

    print(f"[Azure File Share] Uploaded: {file_path}")

    return file_path
