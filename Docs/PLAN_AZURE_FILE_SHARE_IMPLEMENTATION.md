# Plan: Azure File Share Implementation

## Overview

Replace the local W: drive export with Azure File Share, enabling automatic email export from the cloud that's instantly accessible to local users.

**Current Flow:**
```
Azure (Task 4) → Database only → Local script runs manually → W: drive
```

**New Flow:**
```
Azure (Task 4) → Database + Export to Azure File Share → Users see files instantly via mapped drive
```

---

## Configuration (Agreed)

| Item | Value | Status |
|------|-------|--------|
| Storage Account Name | `fdorderprocessingstorage` | ✅ Confirmed |
| File Share Name | `fdorderprocessingfileshare` | ✅ Confirmed |
| Region | `uksouth` | ✅ Confirmed |
| Resource Group | `order-processing-rg` | ✅ Confirmed |
| Drive Letter | (IT preference) | ⏳ Pending |

**Folder Structure (Agreed):**
```
fdorderprocessingstorage (Storage Account)
└── fdorderprocessingfileshare (File Share)
    └── 251212_test/                        ← Date folder (shared by both apps)
        ├── TEXT_CustomerName_20251212_143022_01.eml
        ├── TEXT_CustomerName_20251212_143025_02.eml
        ├── PDF_CustomerName_20251212_150112_01.eml
        └── ...
```

- Both text_orders and pdf_orders apps use the same storage account and file share
- Single date folder for all emails
- Filenames prefixed with `TEXT_` or `PDF_` to identify source

---

## Benefits

- No manual script execution required
- No Task Scheduler needed
- Files appear instantly for local users
- No VPN or tunnel infrastructure
- Single source of truth (cloud storage)
- One storage account serves both apps

---

## Prerequisites

- Azure CLI installed locally (or use Azure Cloud Shell)
- Access to Azure subscription
- GitHub repository access (for secrets)
- IT support for mapping drives on local PCs

---

## Phase 1: Azure Setup

### Step 1.0: Login to Azure CLI

```bash
az login --use-device-code
```

Then find your resource group:
```bash
az webapp list --output table
```

### Step 1.1: Create Storage Account

```bash
# Set variables
RESOURCE_GROUP="order-processing-rg"
STORAGE_ACCOUNT="fdorderprocessingstorage"
LOCATION="uksouth"

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2
```

### Step 1.2: Create File Share

```bash
FILE_SHARE="fdorderprocessingfileshare"

# Create file share
az storage share create \
  --name $FILE_SHARE \
  --account-name $STORAGE_ACCOUNT \
  --quota 100
```

### Step 1.3: Get Storage Account Key

```bash
# Display the key (copy this for GitHub secret)
az storage account keys list \
  --account-name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query "[0].value" -o tsv
```

**Note:** No folder structure needed - date folders are created automatically by the code.

---

## Phase 2: GitHub Configuration

### Step 2.1: Add GitHub Secret

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `AZURE_STORAGE_KEY` | (key from Step 1.3) | Sensitive - must be secret |

**How to add:**
1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AZURE_STORAGE_KEY`
4. Value: Paste the key from Step 1.3

**Note:** Add to BOTH repositories (text_orders and pdf_orders)

### Step 2.2: Add GitHub Variables (or .env)

| Variable Name | Value |
|---------------|-------|
| `AZURE_STORAGE_ACCOUNT` | `fdorderprocessingstorage` |
| `AZURE_FILE_SHARE` | `fdorderprocessingfileshare` |

**Option A - GitHub Variables:**
1. Go to GitHub repo → Settings → Secrets and variables → Actions → Variables
2. Add each variable

**Option B - Add to .env file:**
```env
AZURE_STORAGE_ACCOUNT=fdorderprocessingstorage
AZURE_FILE_SHARE=fdorderprocessingfileshare
AZURE_STORAGE_KEY=your-key-here
```

---

## Phase 3: Code Changes

### Apps to Update

Both apps need the same changes:
- `text_orders` - prefix files with `TEXT_`
- `pdf_orders` - prefix files with `PDF_`

### Step 3.1: Add Azure Storage SDK to requirements.txt

```
azure-storage-file-share==12.15.0
```

### Step 3.2: Create Azure File Share Helper

**New file:** `backend/utils/azure_file_share.py`

```python
"""
Azure File Share helper for uploading email files
"""
import os
from datetime import datetime
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from azure.core.exceptions import ResourceExistsError


def get_connection_string():
    """Build connection string from environment variables"""
    account_name = os.getenv('AZURE_STORAGE_ACCOUNT')
    account_key = os.getenv('AZURE_STORAGE_KEY')
    return f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"


def ensure_date_folder_exists(share_name: str) -> str:
    """Create date folder (YYMMDD_test) if it doesn't exist, return folder path"""
    connection_string = get_connection_string()
    date_folder = datetime.now().strftime("%y%m%d_test")

    # Create directory if it doesn't exist
    directory_client = ShareDirectoryClient.from_connection_string(
        connection_string, share_name, date_folder
    )
    try:
        directory_client.create_directory()
    except ResourceExistsError:
        pass  # Folder already exists

    return date_folder


def upload_email_file(file_content: bytes, filename: str, prefix: str = "TEXT") -> str:
    """
    Upload email file to Azure File Share

    Args:
        file_content: Email content as bytes
        filename: Base name for the file (will be prefixed)
        prefix: "TEXT" or "PDF" to identify source app

    Returns:
        Full path to the uploaded file
    """
    connection_string = get_connection_string()
    share_name = os.getenv('AZURE_FILE_SHARE')

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

    return file_path
```

### Step 3.3: Update task_tidy_emails.py

Restore email handling to Task 4, but export to Azure File Share instead of local drive:

**Changes needed:**
1. Import the new azure_file_share helper
2. Add back Graph API functions (get_access_token, find_folder, etc.)
3. Replace local export with `upload_email_file()`
4. Keep categorize and move email functions

**Key code change:**

```python
# Import at top
from backend.utils.azure_file_share import upload_email_file

# In the email processing loop:
email_content = download_email_content(access_token, user_id, email_id)
filename = f"{safe_subject}_{timestamp}_{sequence_num:02d}.eml"

# TEXT_ORDERS app uses "TEXT" prefix, PDF_ORDERS app uses "PDF" prefix
file_path = upload_email_file(email_content, filename, prefix="TEXT")
```

### Step 3.4: Update .env.example

Add new environment variables:

```env
# Azure File Share (for email export)
AZURE_STORAGE_ACCOUNT=fdorderprocessingstorage
AZURE_FILE_SHARE=fdorderprocessingfileshare
AZURE_STORAGE_KEY=your-storage-account-key
```

---

## Phase 4: IT Setup (Local PCs)

### Step 4.1: Verify Port 445 Access

```powershell
Test-NetConnection -ComputerName fdorderprocessingstorage.file.core.windows.net -Port 445
```

Must return `TcpTestSucceeded: True`

### Step 4.2: Map Network Drive

**Method: Command Prompt (as Administrator)**

```cmd
net use Z: \\fdorderprocessingstorage.file.core.windows.net\fdorderprocessingfileshare /u:AZURE\fdorderprocessingstorage YOUR_STORAGE_KEY /persistent:yes
```

**Method: PowerShell (as Administrator)**

```powershell
$storageAccountName = "fdorderprocessingstorage"
$fileShareName = "fdorderprocessingfileshare"
$storageAccountKey = "YOUR_STORAGE_KEY"

cmd.exe /C "cmdkey /add:`"$storageAccountName.file.core.windows.net`" /user:`"AZURE\$storageAccountName`" /pass:`"$storageAccountKey`""
New-PSDrive -Name Z -PSProvider FileSystem -Root "\\$storageAccountName.file.core.windows.net\$fileShareName" -Persist
```

### Step 4.3: Verify Access

1. Open File Explorer
2. Navigate to Z: drive (or chosen letter)
3. Should see date folders with email files after processing

---

## Phase 5: Testing

### Step 5.1: Test Azure File Share Upload (Manual)

```python
# Run from backend folder
from utils.azure_file_share import upload_email_file

test_content = b"Test email content"
path = upload_email_file(test_content, "test_email.eml", prefix="TEXT")
print(f"Uploaded to: {path}")
```

### Step 5.2: Test End-to-End

1. Start a job via the web app
2. Process through Tasks 1-4
3. Verify:
   - [ ] Order data inserted to database
   - [ ] Email exported to Azure File Share
   - [ ] Email categorized as Green in Outlook
   - [ ] Email moved to ProcessedOrders folder
   - [ ] File visible on mapped drive

### Step 5.3: Verify Local Access

1. On factory PC with mapped drive
2. Navigate to Z:\YYMMDD_test\
3. Confirm .eml files are visible with TEXT_ or PDF_ prefix

---

## Phase 6: Cleanup (After Successful Testing)

### Step 6.1: Remove Local Script

The following files are no longer needed:

- [ ] `scripts/export_emails_to_w_drive.py`
- [ ] `export_emails.bat`

### Step 6.2: Update Documentation

- [ ] Update CLAUDE.md to reflect new architecture
- [ ] Archive old W: drive documentation

---

## Rollback Plan

If issues arise, revert to local script approach:

1. Revert code changes to task_tidy_emails.py
2. Re-enable local script (`export_emails.bat`)
3. Set up Task Scheduler as backup

The local script approach remains as a documented fallback.

---

## Cost Estimate

| Resource | Cost |
|----------|------|
| Azure File Share | ~$0.06/GB/month |
| Storage transactions | ~$0.01 per 10,000 operations |
| **Estimated monthly** | **< $5/month** (assuming < 50GB storage) |

---

## Timeline

| Phase | Description | Owner |
|-------|-------------|-------|
| Phase 1 | Azure Setup (CLI) | Developer |
| Phase 2 | GitHub Configuration | Developer |
| Phase 3 | Code Changes | Developer |
| Phase 4 | IT Setup (Drive Mapping) | IT |
| Phase 5 | Testing | Developer + IT |
| Phase 6 | Cleanup | Developer |

---

## Files to Modify

### text_orders

| File | Action |
|------|--------|
| `requirements.txt` | Add azure-storage-file-share |
| `backend/utils/azure_file_share.py` | Create new |
| `backend/tasks/task_tidy_emails.py` | Restore email handling, use Azure upload |
| `.env` | Add Azure storage variables |
| `.env.example` | Add Azure storage variables |

### pdf_orders

| File | Action |
|------|--------|
| `requirements.txt` | Add azure-storage-file-share |
| `backend/utils/azure_file_share.py` | Create new (same as text_orders) |
| `backend/tasks/task_tidy_emails.py` | Update to use Azure upload with "PDF" prefix |
| `.env` | Add Azure storage variables |
| `.env.example` | Add Azure storage variables |

---

## Questions Resolved

- [x] Storage Account name: `fdorderprocessingstorage`
- [x] File Share name: `fdorderprocessingfileshare`
- [x] Azure region: `uksouth`
- [x] Folder structure: Single date folder, prefixed filenames
- [x] Resource Group: `order-processing-rg`
- [ ] Drive letter: (IT preference - not blocking)
