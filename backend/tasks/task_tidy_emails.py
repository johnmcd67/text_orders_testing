"""
Task 4: Database Export + Email Tidy

Inserts approved orders into the database, then:
1. Exports email files to Azure File Share (instantly accessible via mapped drive)
2. Categorizes processed emails as Green in Outlook
3. Moves emails from WIP_Text_Orders to ProcessedOrders_Text_Orders folder
"""

import os
import urllib.parse
from datetime import datetime

import pandas as pd
import psycopg
import requests

from backend.celery_app import celery_app
from backend.database import (
    update_job_status,
    update_job_progress_with_message,
    complete_job,
    fail_job,
)
from backend.subagents.db_export import export_to_database
from backend.utils.blob_storage import load_csv, save_csv
from backend.utils.azure_file_share import upload_email_file

# Base path for email directory (mapped drive path)
EMAIL_DIRECTORY_BASE = r"W:\PEDIDOS Y ALBARANES\PEDIDOS DIGITAL"


# Microsoft Graph API functions
def get_access_token() -> str:
    """Get Microsoft Graph API access token."""
    tenant_id = os.getenv('MICROSOFT_TENANT_ID')
    client_id = os.getenv('MICROSOFT_CLIENT_ID')
    client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }

    response = requests.post(token_url, data=token_data, timeout=30)
    response.raise_for_status()
    return response.json()['access_token']


def find_folder(access_token: str, user_id: str, folder_path: str) -> str:
    """
    Navigate to a folder by path (e.g., 'Inbox/FD/ProcessedOrders_Text_Orders').

    Returns:
        str: Folder ID
    """
    headers = {'Authorization': f'Bearer {access_token}'}

    parts = folder_path.split('/')
    current_folder_id = None

    for i, part in enumerate(parts):
        if i == 0:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders"
        else:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{current_folder_id}/childFolders"

        # Handle pagination - collect all folders across all pages
        folders = []
        current_url = f"{url}?$top=999"
        while current_url:
            response = requests.get(current_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            folders.extend(data.get('value', []))
            current_url = data.get('@odata.nextLink')

        folder = next((f for f in folders if f['displayName'] == part), None)
        if not folder:
            raise ValueError(f"Folder '{part}' not found in path '{folder_path}'")

        current_folder_id = folder['id']

    return current_folder_id


def get_emails_from_folder(access_token: str, user_id: str, folder_id: str) -> dict:
    """Get all emails from a folder. Returns dict mapping email_id -> email_data."""
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{folder_id}/messages?$top=500"

    all_emails = {}
    while url:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        for email in data.get('value', []):
            email_id = email['id']
            all_emails[email_id] = {
                'id': email_id,
                'subject': email.get('subject', 'No Subject'),
                'receivedDateTime': email.get('receivedDateTime', '')
            }

        url = data.get('@odata.nextLink')

    return all_emails


def download_email_content(access_token: str, user_id: str, email_id: str) -> bytes:
    """Download email as .eml file content."""
    headers = {'Authorization': f'Bearer {access_token}'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}/$value"

    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.content


def categorize_email_green(access_token: str, user_id: str, email_id: str) -> bool:
    """Categorize email with green color."""
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}"

    for category_name in ["Green", "Green category", "Category 3", "Processed"]:
        try:
            response = requests.patch(url, json={"categories": [category_name]}, headers=headers, timeout=30)
            response.raise_for_status()
            return True
        except Exception:
            continue

    return False


def move_email_to_folder(access_token: str, user_id: str, email_id: str, destination_folder_id: str) -> bool:
    """Move email to destination folder."""
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}/move"

    response = requests.post(url, json={"destinationId": destination_folder_id}, headers=headers, timeout=30)
    response.raise_for_status()
    return True


def normalize_email_id(email_id: str) -> str:
    """Normalize email ID for comparison (convert Base64 to URL-safe format)."""
    return email_id.replace('+', '-').replace('/', '-')


def update_email_directory(email_id: str, file_path: str) -> bool:
    """
    Update email_directory in ai_tool_output_table for all rows with matching email_id.

    Args:
        email_id: The email ID (entry_id/email_id in the database)
        file_path: Full path to the email file (e.g., W:\...\251212_test\TEXT_...eml)

    Returns:
        bool: True if update was successful
    """
    database_url = os.getenv('DATABASE_URL')
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                # Update all rows with this email_id
                cursor.execute(
                    "UPDATE public.ai_tool_output_table SET email_directory = %s WHERE email_id = %s",
                    (file_path, email_id)
                )
                conn.commit()
                rows_updated = cursor.rowcount
                if rows_updated > 0:
                    print(f"[Task 4]   Updated email_directory for {rows_updated} row(s)")
                return rows_updated > 0
    except Exception as e:
        print(f"[Task 4]   Failed to update email_directory: {e}")
        return False


def get_email_ids_from_database() -> list:
    """
    Get unique email IDs from ai_tool_output_table.
    Only returns email IDs that have been successfully inserted into the database.
    """
    database_url = os.getenv('DATABASE_URL')
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT DISTINCT email_id FROM public.ai_tool_output_table WHERE email_id IS NOT NULL"
                )
                rows = cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        print(f"[Task 4] Failed to query email IDs from database: {e}")
        return []


def process_emails_to_azure(df: pd.DataFrame, job_id: int) -> dict:
    """
    Process emails: upload to Azure File Share, categorize, and move.

    Args:
        df: DataFrame containing order data with email_id column
        job_id: Job ID for logging

    Returns:
        dict: Statistics about processed emails
    """
    stats = {
        'exported': 0,
        'categorized': 0,
        'moved': 0,
        'failed': 0,
        'skipped': 0
    }

    # Get unique email IDs from database (only emails that were successfully saved)
    email_ids = get_email_ids_from_database()
    if not email_ids:
        print(f"[Task 4] No email IDs found in database")
        return stats

    print(f"[Task 4] Found {len(email_ids)} unique email IDs in database")

    try:
        # Get Graph API access token
        access_token = get_access_token()
        user_id = os.getenv('MICROSOFT_OBJECT_ID')

        # Find folders
        wip_folder_id = find_folder(access_token, user_id, "Inbox/Test_Env/WIP_Text_Orders")
        processed_folder_id = find_folder(access_token, user_id, "Inbox/Test_Env/ProcessedOrders_Text_Orders")

        # Get emails from WIP folder
        folder_emails = get_emails_from_folder(access_token, user_id, wip_folder_id)
        print(f"[Task 4] Found {len(folder_emails)} emails in WIP folder")

        # Create lookup: normalized DB ID -> original DB ID
        db_normalized_lookup = {normalize_email_id(eid): eid for eid in email_ids}

        # Process each email
        for folder_email_id, email_data in folder_emails.items():
            if folder_email_id not in db_normalized_lookup:
                continue

            original_email_id = db_normalized_lookup[folder_email_id]
            subject = email_data.get('subject', 'No subject')[:50]

            try:
                print(f"[Task 4] Processing: {subject}...")

                # Download email content
                email_content = download_email_content(access_token, user_id, folder_email_id)

                # Build filename
                safe_subject = "".join(
                    c for c in email_data['subject'][:30]
                    if c.isalnum() or c in (' ', '-', '_')
                ).strip() or "email"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"{safe_subject}_{timestamp}_{stats['exported'] + 1:02d}.eml"

                # Upload to Azure File Share with TEXT_ prefix
                relative_path = upload_email_file(email_content, filename, prefix="TEXT")
                stats['exported'] += 1
                print(f"[Task 4]   Exported to Azure File Share: {relative_path}")

                # Build full path for database (base + relative with backslashes)
                relative_path_windows = relative_path.replace('/', '\\')
                full_path = f"{EMAIL_DIRECTORY_BASE}\\{relative_path_windows}"

                # Update email_directory in ai_tool_output_table
                update_email_directory(original_email_id, full_path)

                # Categorize as Green
                if categorize_email_green(access_token, user_id, folder_email_id):
                    stats['categorized'] += 1
                    print(f"[Task 4]   Categorized as Green")

                # Move to ProcessedOrders folder
                if move_email_to_folder(access_token, user_id, folder_email_id, processed_folder_id):
                    stats['moved'] += 1
                    print(f"[Task 4]   Moved to ProcessedOrders_Text_Orders")

            except Exception as e:
                print(f"[Task 4]   Failed: {e}")
                stats['failed'] += 1

    except Exception as e:
        print(f"[Task 4] Email processing error: {e}")
        # Don't fail the whole job - database export already succeeded
        stats['error'] = str(e)

    return stats


@celery_app.task(bind=True)
def tidy_emails_task(self, job_id: int):
    """
    Export approved orders to database, then process emails.

    Args:
        job_id: ID of the job in job_runs table

    Returns:
        dict: Status and statistics
    """
    try:
        # Update job status to running
        update_job_status(job_id, "running")
        update_job_progress_with_message(job_id, 0, "Initializing database export...")

        print(f"[Task 4] Starting database export process...")

        # Step 1: Read approved order data
        update_job_progress_with_message(job_id, 10, "Reading approved order data...")
        print(f"[Task 4] Reading order_details.csv for database insertion...")

        df = load_csv('order_details.csv')

        # Convert DataFrame to list of order dictionaries
        orders_to_insert = []
        for _, row in df.iterrows():
            order = {
                "orderno": int(float(row["orderno"])) if pd.notna(row["orderno"]) else 0,
                "customerid": int(float(row["customerid"])) if pd.notna(row["customerid"]) and row["customerid"] != 0 else 0,
                "customer_name": row["customer_name"] if pd.notna(row["customer_name"]) else None,
                "sku": row["sku"] if pd.notna(row["sku"]) else None,
                "quantity": int(float(row["quantity"])) if pd.notna(row["quantity"]) else 0,
                "reference_no": row["reference_no"] if pd.notna(row["reference_no"]) else None,
                "valve": row["valve"] if pd.notna(row["valve"]) else "no",
                "delivery_address": row["delivery_address"] if pd.notna(row["delivery_address"]) else None,
                "cpsd": row["cpsd"] if pd.notna(row["cpsd"]) else None,
                "entry_id": row["entry_id"] if pd.notna(row["entry_id"]) else None,
                "option_sku": row["option_sku"] if pd.notna(row["option_sku"]) else None,
                "option_qty": int(float(row["option_qty"])) if pd.notna(row["option_qty"]) else None,
                "telephone_number": row["telephone_number"] if pd.notna(row["telephone_number"]) else None,
                "contact_name": row["contact_name"] if pd.notna(row["contact_name"]) else None,
                "job_id": job_id,
            }
            orders_to_insert.append(order)

        print(f"[Task 4] Loaded {len(orders_to_insert)} orders from storage")

        # Step 2: Export to database
        update_job_progress_with_message(job_id, 30, f"Inserting {len(orders_to_insert)} orders into database...")
        print(f"[Task 4] Exporting {len(orders_to_insert)} orders to database...")
        export_result = export_to_database(orders_to_insert)

        print(f"[Task 4] Database export complete:")
        print(f"[Task 4]   Success: {export_result['success_count']}")
        print(f"[Task 4]   Failed: {export_result['failed_count']}")

        # Step 3: Write failed_orders.csv if there are failures
        if export_result["failed_orders"]:
            update_job_progress_with_message(job_id, 50, "Writing failed orders report...")
            df_failed = pd.DataFrame(export_result["failed_orders"])
            saved_path = save_csv(df_failed, 'failed_orders.csv')
            print(f"[Task 4] Writing failed_orders.csv: {saved_path}")
        else:
            print(f"[Task 4] No failed orders - all {export_result['success_count']} orders inserted successfully")

        # Step 4: Process emails (export to Azure File Share, categorize, move)
        update_job_progress_with_message(job_id, 60, "Processing emails...")
        email_stats = process_emails_to_azure(df, job_id)

        # Summary
        print(f"[Task 4] " + "=" * 80)
        print(f"[Task 4] TASK 4 - COMPLETE")
        print(f"[Task 4] " + "=" * 80)
        print(f"[Task 4] Database: {export_result['success_count']} inserted, {export_result['failed_count']} failed")
        print(f"[Task 4] Emails: {email_stats['exported']} exported, {email_stats['categorized']} categorized, {email_stats['moved']} moved")
        print(f"[Task 4] " + "=" * 80)

        # Build completion message
        db_msg = f"{export_result['success_count']} order{'' if export_result['success_count'] == 1 else 's'} saved"
        email_msg = f", {email_stats['exported']} email{'' if email_stats['exported'] == 1 else 's'} exported"
        completion_message = f"{db_msg}{email_msg}"

        # Update final progress message before completing
        update_job_progress_with_message(job_id, 100, completion_message)

        # Mark job as completed
        complete_job(job_id)

        return {
            "status": "completed",
            "database": {
                "success_count": export_result['success_count'],
                "failed_count": export_result['failed_count']
            },
            "emails": email_stats
        }

    except Exception as e:
        # Fatal error - mark job as failed
        error_message = f"Task 4 failed: {str(e)}"
        print(f"[Task 4] {error_message}")
        fail_job(job_id, error_message)
        raise
