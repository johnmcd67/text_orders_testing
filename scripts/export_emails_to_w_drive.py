"""
Local Script: Export Emails to W: Drive

This script runs locally (not on Azure) to export processed emails to the W: drive.
It queries PostgreSQL for emails where email_directory is NULL, downloads them from
Outlook's WIP_Text_Orders folder, saves them to the W: drive, categorizes them as Green,
and moves them to ProcessedOrders_Text_Orders folder.

Workflow:
    1. Query DB for email_ids where email_directory IS NULL
    2. Fetch emails from WIP_Text_Orders folder
    3. For each match:
       - Download .eml content
       - Save to W: drive (W:\\PEDIDOS Y ALBARANES\\PEDIDOS DIGITAL\\YYMMDD\\YYMMDDAI\\)
       - Categorize email as Green
       - Move email from WIP → ProcessedOrders folder
       - Update email_directory in database

Usage:
    python scripts/export_emails_to_w_drive.py

Prerequisites:
    - Access to W: drive (W:\\PEDIDOS Y ALBARANES\\PEDIDOS DIGITAL)
    - .env file with DATABASE_URL and Microsoft Graph API credentials
"""

import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
import requests
import psycopg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
EXPORT_BASE_PATH = Path(r"W:\PEDIDOS Y ALBARANES\PEDIDOS DIGITAL")
DATE_FOLDER_FORMAT = "%y%m%d"  # e.g., 251211 (parent folder, AI subfolder added separately)


def get_access_token():
    """Get Microsoft Graph API access token"""
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

    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    return response.json()['access_token']


def get_db_connection():
    """Get database connection"""
    database_url = os.getenv('DATABASE_URL')
    return psycopg.connect(database_url)


def get_emails_without_directory(conn):
    """Query database for emails where email_directory is NULL"""
    cursor = conn.cursor()
    query = """
        SELECT DISTINCT email_id
        FROM public.ai_tool_output_table
        WHERE email_directory IS NULL
        AND email_id IS NOT NULL
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return [row[0] for row in rows]


def update_email_directory(conn, email_id, file_path):
    """Update email_directory field in database"""
    cursor = conn.cursor()
    query = "UPDATE public.ai_tool_output_table SET email_directory = %s WHERE email_id = %s"
    cursor.execute(query, (file_path, email_id))
    conn.commit()
    rows_updated = cursor.rowcount
    cursor.close()
    return rows_updated > 0


def find_folder(access_token, user_id, folder_path):
    """Navigate to a folder by path (e.g., 'Inbox/FD/ProcessedOrders_Text_Orders')"""
    headers = {'Authorization': f'Bearer {access_token}'}

    parts = folder_path.split('/')
    current_folder_id = None

    for i, part in enumerate(parts):
        if i == 0:
            # First level - search in root mail folders
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders"
        else:
            # Subsequent levels - search in child folders
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{current_folder_id}/childFolders"

        # Handle pagination - collect all folders across all pages
        folders = []
        current_url = f"{url}?$top=999"
        while current_url:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            folders.extend(data.get('value', []))
            current_url = data.get('@odata.nextLink')

        folder = next((f for f in folders if f['displayName'] == part), None)
        if not folder:
            raise ValueError(f"Folder '{part}' not found in path '{folder_path}'")

        current_folder_id = folder['id']

    return current_folder_id


def get_emails_from_folder(access_token, user_id, folder_id):
    """Get all emails from a folder (IDs are kept as-is from Graph API)"""
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{folder_id}/messages?$top=500"

    all_emails = {}
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for email in data.get('value', []):
            # Use email ID as-is from Graph API (don't normalize)
            email_id = email['id']
            all_emails[email_id] = {
                'id': email_id,
                'subject': email.get('subject', 'No Subject'),
                'receivedDateTime': email.get('receivedDateTime', '')
            }

        url = data.get('@odata.nextLink')

    return all_emails


def download_email_content(access_token, user_id, email_id):
    """Download email as .eml file content"""
    headers = {'Authorization': f'Bearer {access_token}'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}/$value"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content


def categorize_email_green(access_token, user_id, email_id):
    """Categorize email with green color"""
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}"

    # Try different green category names
    for category_name in ["Green", "Green category", "Category 3", "Processed"]:
        try:
            response = requests.patch(url, json={"categories": [category_name]}, headers=headers)
            response.raise_for_status()
            return True
        except:
            continue

    return False


def move_email_to_folder(access_token, user_id, email_id, destination_folder_id):
    """Move email to destination folder"""
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    encoded_email_id = urllib.parse.quote(email_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{encoded_email_id}/move"

    response = requests.post(url, json={"destinationId": destination_folder_id}, headers=headers)
    response.raise_for_status()
    return True


def export_email_to_w_drive(access_token, user_id, email_data, email_id, sequence_num):
    """Export email to W: drive"""
    date_str = datetime.now().strftime(DATE_FOLDER_FORMAT)
    date_folder = EXPORT_BASE_PATH / date_str / f"{date_str}AI"
    date_folder.mkdir(parents=True, exist_ok=True)

    subject = email_data.get('subject', 'No subject')

    # Clean filename
    safe_subject = "".join(c for c in subject[:30] if c.isalnum() or c in (' ', '-', '_')).strip() or "email"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{safe_subject}_{timestamp}_{sequence_num:02d}.eml"
    file_path = date_folder / filename

    # Download and save email
    email_content = download_email_content(access_token, user_id, email_data['id'])
    with open(file_path, 'wb') as f:
        f.write(email_content)

    return str(file_path)


def normalize_email_id(email_id):
    """Normalize email ID for comparison (convert Base64 to URL-safe format)"""
    return email_id.replace('+', '-').replace('/', '-')


def main():
    print("=" * 80)
    print("EMAIL EXPORT TO W: DRIVE (Text Orders)")
    print("=" * 80)

    # Check W: drive access
    if not EXPORT_BASE_PATH.exists():
        print(f"ERROR: Cannot access {EXPORT_BASE_PATH}")
        print("Make sure the W: drive is mapped and accessible.")
        sys.exit(1)

    print(f"Export path: {EXPORT_BASE_PATH}")

    # Connect to database
    print("\nConnecting to database...")
    conn = get_db_connection()

    # Get emails without directory
    print("Querying for emails without email_directory...")
    email_ids = get_emails_without_directory(conn)
    print(f"Found {len(email_ids)} emails to export")

    if not email_ids:
        print("No emails to export. Exiting.")
        conn.close()
        return

    # Get Graph API access token
    print("\nGetting Microsoft Graph API access token...")
    access_token = get_access_token()
    user_id = os.getenv('MICROSOFT_OBJECT_ID')

    # Find WIP folder (source folder where emails are waiting)
    print("Finding WIP_Text_Orders folder...")
    wip_folder_id = find_folder(access_token, user_id, "Inbox/FD/WIP_Text_Orders")

    # Find ProcessedOrders folder (destination for after export)
    print("Finding ProcessedOrders_Text_Orders folder...")
    processed_folder_id = find_folder(access_token, user_id, "Inbox/FD/ProcessedOrders_Text_Orders")

    # Get emails from WIP folder
    print("Fetching emails from WIP_Text_Orders folder...")
    folder_emails = get_emails_from_folder(access_token, user_id, wip_folder_id)
    print(f"Found {len(folder_emails)} emails in WIP folder")

    # Match and export
    exported_count = 0
    categorized_count = 0
    moved_count = 0
    failed_count = 0

    # Create lookup: normalized DB ID -> original DB ID
    # DB IDs have +/ characters, Graph API IDs use -_ (URL-safe)
    db_normalized_lookup = {normalize_email_id(eid): eid for eid in email_ids}

    print(f"\nLooking for {len(db_normalized_lookup)} DB email IDs in {len(folder_emails)} folder emails...")

    print("\nProcessing emails...")
    for folder_email_id, email_data in folder_emails.items():
        # folder_email_id is already URL-safe from Graph API
        # Check if it matches any normalized DB ID
        if folder_email_id in db_normalized_lookup:
            original_db_email_id = db_normalized_lookup[folder_email_id]
            print(f"\n[{exported_count + 1}] Processing: {email_data['subject'][:50]}...")

            try:
                # Export to W: drive
                file_path = export_email_to_w_drive(
                    access_token, user_id, email_data, original_db_email_id, exported_count + 1
                )
                print(f"    ✓ Exported to: {Path(file_path).name}")

                # Categorize email as Green
                if categorize_email_green(access_token, user_id, folder_email_id):
                    categorized_count += 1
                    print(f"    ✓ Categorized as Green")

                # Move email from WIP to ProcessedOrders
                if move_email_to_folder(access_token, user_id, folder_email_id, processed_folder_id):
                    moved_count += 1
                    print(f"    ✓ Moved to ProcessedOrders_Text_Orders")

                # Update database
                update_email_directory(conn, original_db_email_id, file_path)
                print(f"    ✓ Database updated")

                exported_count += 1

            except Exception as e:
                print(f"    ✗ Failed: {e}")
                failed_count += 1

    # Close database connection
    conn.close()

    # Summary
    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"Successfully exported: {exported_count}")
    print(f"Successfully categorized: {categorized_count}")
    print(f"Successfully moved: {moved_count}")
    print(f"Failed: {failed_count}")
    date_str = datetime.now().strftime(DATE_FOLDER_FORMAT)
    print(f"Export location: {EXPORT_BASE_PATH / date_str / f'{date_str}AI'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
