# Plan: Text Orders - W: Drive Export

## Changes Required

### 1. Modify `backend/tasks/task_tidy_emails.py`

**Remove:**
- Export to desktop code (lines 364-367)
- Move email code (lines 378-380)
- `dest_folder_id` lookup (lines 328-331)
- `moved_count` variable
- `update_email_directory_in_database()` call (line 370)

**Keep only:**
- Database insertion
- Categorize as Green

### 2. Create `scripts/export_emails_to_w_drive.py`

Copy from pdf_orders and change:
- `WIP_PDF_Orders` → `WIP_Text_Orders`
- `ProcessedOrders_PDF_Orders` → `ProcessedOrders_Text_Orders`

## Configuration

- Export path: `W:\PEDIDOS Y ALBARANES\PEDIDOS DIGITAL`
- Date folder: `YYMMDD_test`
- WIP folder: `Inbox/FD/WIP_Text_Orders`
- ProcessedOrders: `Inbox/FD/ProcessedOrders_Text_Orders`

## Usage

```bash
python scripts/export_emails_to_w_drive.py
```
