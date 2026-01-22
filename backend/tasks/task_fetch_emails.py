"""
Task 1: Fetch Emails from Outlook
Fetches text-only emails from WIP_Text_Orders folder
Saves raw email data to temp/emails_raw.json
"""
import os
import re
from html import unescape
import requests

from backend.celery_app import celery_app
from backend.database import (
    update_job_status,
    update_job_progress_with_message,
    fail_job
)
from backend.utils.blob_storage import save_json, cleanup_temp_dir


def get_access_token(tenant_id, client_id, client_secret):
    """Get Microsoft Graph API access token"""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }

    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()['access_token']


def find_folder_by_path(access_token, user_id, folder_path):
    """
    Navigate folder hierarchy and return folder ID
    folder_path: e.g., "Inbox/FD/WIP_Text_Orders"
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Split path into segments
    path_segments = folder_path.split('/')

    # Start with root folders
    current_folder_id = None

    for segment in path_segments:
        if current_folder_id is None:
            # For "Inbox", use the well-known folder endpoint
            if segment.lower() == 'inbox':
                url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/inbox"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                folder_data = response.json()
                current_folder_id = folder_data['id']
                print(f"[Task 1] Found Inbox folder: {current_folder_id}")
                continue
            else:
                # Search in root mail folders
                url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders"
        else:
            # Search in child folders
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{current_folder_id}/childFolders"

        # Handle pagination - collect all folders across all pages
        folders = []
        current_url = url
        params = {'$top': 999}  # Request more items per page
        while current_url:
            response = requests.get(current_url, headers=headers, params=params if current_url == url else None)
            response.raise_for_status()
            data = response.json()
            folders.extend(data.get('value', []))
            current_url = data.get('@odata.nextLink')  # Get next page if available
            params = None  # Don't send params again for nextLink

        # Debug: print available folders
        available_names = [f.get('displayName', '') for f in folders]
        print(f"[Task 1] Searching for '{segment}' in folders: {available_names}")

        # Find matching folder (case-insensitive)
        found = False
        for folder in folders:
            if folder.get('displayName', '').lower() == segment.lower():
                current_folder_id = folder['id']
                found = True
                print(f"[Task 1] Found folder '{segment}': {current_folder_id}")
                break

        if not found:
            available_names_str = ', '.join(available_names) if available_names else 'none'
            raise Exception(f"Folder '{segment}' not found in path '{folder_path}'. Available folders: {available_names_str}")

    return current_folder_id


def get_messages_from_folder(access_token, user_id, folder_id):
    """Get all messages from a specific folder"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{folder_id}/messages"
    params = {
        '$top': 999
    }

    messages = []

    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        messages.extend(data.get('value', []))
        url = data.get('@odata.nextLink')  # Handle pagination
        params = None  # Don't send params again for nextLink

    return messages


def strip_html(html_content):
    """Strip HTML tags and return plain text"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Unescape HTML entities
    text = unescape(text)
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


@celery_app.task(bind=True)
def fetch_emails_task(self, job_id: int):
    """
    Fetch emails from Outlook WIP_Text_Orders folder

    Args:
        job_id: ID of the job in job_runs table

    Returns:
        dict: Status and count of emails fetched
    """
    try:
        # Update job status to running
        update_job_status(job_id, "running")
        update_job_progress_with_message(job_id, 0, "Authenticating with Microsoft Graph API...")

        # Get environment variables
        tenant_id = os.getenv('MICROSOFT_TENANT_ID')
        client_id = os.getenv('MICROSOFT_CLIENT_ID')
        client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        user_id = os.getenv('MICROSOFT_OBJECT_ID')

        if not all([tenant_id, client_id, client_secret, user_id]):
            raise ValueError("Missing required Microsoft Graph API environment variables")

        # Setup temp directory (clean slate for new job)
        print(f"[Task 1] Cleaning up existing temp directory...")
        cleanup_temp_dir()

        # Get access token
        print("[Task 1] Authenticating with Microsoft Graph API...")
        access_token = get_access_token(tenant_id, client_id, client_secret)

        # Find the target folder
        update_job_progress_with_message(job_id, 10, "Finding Outlook folder: Inbox/FD/WIP_Text_Orders...")
        print("[Task 1] Finding Outlook folder: Inbox/FD/WIP_Text_Orders...")
        folder_path = "Inbox/FD/WIP_Text_Orders"
        folder_id = find_folder_by_path(access_token, user_id, folder_path)
        print(f"[Task 1] Found folder ID: {folder_id}")

        # Get all messages
        update_job_progress_with_message(job_id, 20, "Fetching emails from Outlook folder...")
        print("[Task 1] Fetching messages from folder...")
        messages = get_messages_from_folder(access_token, user_id, folder_id)
        print(f"[Task 1] Found {len(messages)} messages")

        if len(messages) == 0:
            print("[Task 1] No messages found in folder. Nothing to process.")
            return {
                "status": "completed",
                "emails_fetched": 0,
                "message": "No emails found in folder"
            }

        # Process each message
        all_emails_raw = []

        for idx, message in enumerate(messages, 1):
            # Update progress
            progress = 20 + int((idx / len(messages)) * 70)  # 20% to 90%
            msg = f"Processing email {idx}/{len(messages)}..."
            update_job_progress_with_message(job_id, progress, msg)

            print(f"[Task 1] Processing message {idx}/{len(messages)}: {message.get('subject', 'No Subject')[:50]}")

            # Extract email metadata
            message_id = message['id']
            from_addr = message.get('from', {}).get('emailAddress', {}).get('address', '')

            to_addrs = ', '.join([r.get('emailAddress', {}).get('address', '')
                                 for r in message.get('toRecipients', [])])

            cc_addrs = ', '.join([r.get('emailAddress', {}).get('address', '')
                                 for r in message.get('ccRecipients', [])])

            subject = message.get('subject', '')
            date = message.get('receivedDateTime', '')

            # Extract raw email body
            body_content = message.get('body', {}).get('content', '')
            body_type = message.get('body', {}).get('contentType', 'text')

            if body_type == 'html':
                body_raw = strip_html(body_content)
            else:
                body_raw = body_content

            # Store raw email data
            email_data = {
                'message_id': message_id,
                'from': from_addr,
                'to': to_addrs,
                'cc': cc_addrs,
                'subject': subject,
                'date': date,
                'body_raw': body_raw
            }

            all_emails_raw.append(email_data)

        # Save metadata to JSON (Azure Blob or local)
        update_job_progress_with_message(job_id, 90, "Saving email data...")
        saved_path = save_json(all_emails_raw, 'emails_raw.json')

        print(f"[Task 1] ✓ Task 1 Complete")
        print(f"[Task 1]   Total emails fetched: {len(all_emails_raw)}")
        print(f"[Task 1]   Metadata saved to: {saved_path}")

        update_job_progress_with_message(job_id, 100, f"Email fetching complete. Found {len(all_emails_raw)} emails.")

        return {
            "status": "completed",
            "emails_fetched": len(all_emails_raw),
            "emails_processed": len(all_emails_raw)
        }

    except Exception as e:
        # Fatal error - mark job as failed
        error_message = f"Task 1 (Email Fetching) failed: {str(e)}"
        print(f"[Task 1] ✗ {error_message}")
        fail_job(job_id, error_message)
        raise

