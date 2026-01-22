# Text Orders Web Application - Implementation Plan

## Overview
Combine 3 separate text order projects into a unified web application similar to pdf_orders:
1. **Project 1** (text_orders): Extract emails from Outlook → output_cleaned.csv
2. **Project 2** (FD_OrderIntake_Anthropic): Process CSV → extract data → PostgreSQL
3. **Project 3** (ExportEmailFromInbox): Export emails → update database paths

## Architecture
- **Backend**: FastAPI + Celery + Redis (same as pdf_orders)
- **Frontend**: React + TypeScript (separate app, similar structure)
- **Database**: Same tables as pdf_orders (`ai_tool_input_table_from_web_app`, `ai_tool_output_table`, `job_runs`)
- **Workflow**: Task 1 (Fetch) → Task 2 (Extract Original Emails) → Task 3 (Extract Data) → [Review] → Task 4 (Tidy)

## Key Differences from PDF Orders
- **No OCR**: Text emails don't need PDF processing
- **Email Extraction**: Task 2 extracts original emails from forwarded threads (replaces manual Claude Code step)
- **Folder Paths**: `WIP_Text_Orders` → `ProcessedOrders_Text_Orders` (vs PDF folders)
- **Input Format**: Raw email threads (vs PDF attachments)

## Implementation Steps

### Phase 1: Backend Structure
1. **Create backend directory structure**
   - Copy structure from pdf_orders/backend
   - Adapt for text orders workflow

2. **Core files to create/adapt**:
   - `backend/main.py` - FastAPI app (similar endpoints)
   - `backend/celery_app.py` - Celery configuration
   - `backend/database.py` - Database operations (reuse from pdf_orders)
   - `backend/models.py` - Pydantic models (reuse from pdf_orders)
   - `backend/utils/` - Helper modules (anthropic_helper, logger, database)

3. **Subagents** (copy from pdf_orders):
   - All subagents are identical: customer_id, sku_extraction, reference_no, valve_detection, delivery_address, cpsd_extraction, options_extraction, db_export
   - Copy entire `backend/subagents/` directory
   - Copy `backend/prompts/` directory

### Phase 2: Celery Tasks
1. **Task 1: Fetch Emails** (`backend/tasks/task_fetch_emails.py`)
   - Fetch from `Inbox/FD/WIP_Text_Orders` folder
   - No PDF attachments (text-only emails)
   - Save raw email data to `temp/emails_raw.json`
   - Similar to pdf_orders Task 1 but simplified (no PDF download)

2. **Task 2: Extract Original Emails** (`backend/tasks/task_extract_emails.py`)
   - **NEW TASK** - Replaces manual Claude Code step
   - Read `temp/emails_raw.json`
   - For each email, call Anthropic API to extract original email from forwarded thread
   - Use logic from `TEXT_ORDERS_PROMPT.md`:
     - Find LAST "De:" marker (original email)
     - Extract original email metadata (from, subject, date)
     - Split body/footer using Spanish markers
     - Preserve full thread body
   - Save to `temp/emails_extracted.json` (format matching finalize_text_orders.py output)
   - Auto-chain to Task 3

3. **Task 3: Extract Data** (`backend/tasks/task_extract_data.py`)
   - Read `temp/emails_extracted.json`
   - Convert to CSV format (like finalize_text_orders.py does)
   - Process through subagents (same as pdf_orders Task 3)
   - Generate `temp/order_details.csv`
   - Pause at `awaiting_review_data` status

4. **Task 4: Tidy Emails** (`backend/tasks/task_tidy_emails.py`)
   - Insert approved orders into database
   - Export emails to Desktop/ProcessedEmails folder
   - Update `email_directory` in database
   - Categorize emails as "Green"
   - Move to `Inbox/FD/ProcessedOrders_Text_Orders` folder
   - Similar to pdf_orders Task 4 but different folder names

### Phase 3: Frontend Application
1. **Create React app structure** (separate from pdf_orders)
   - Initialize in `frontend/` directory
   - Use same tech stack: React + TypeScript + Vite + Tailwind + shadcn/ui

2. **Components to create** (similar to pdf_orders):
   - `LandingPage.tsx` - Start job button
   - `Dashboard.tsx` - Main job management interface
   - `ProgressTracker.tsx` - Real-time progress updates
   - `DataReviewTable.tsx` - Review/edit extracted orders
   - `ResultsDownload.tsx` - Download CSV results
   - `ErrorDisplay.tsx` - Error handling
   - UI components (button, card, table, etc.)

3. **API integration**:
   - `api/jobsApi.ts` - Job endpoints
   - `api/promptsApi.ts` - Prompt viewing
   - `hooks/useJobPolling.ts` - Polling for job status

### Phase 4: Configuration & Setup
1. **Environment variables**:
   - Same as pdf_orders: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, Microsoft Graph credentials
   - Add to `.env` file

2. **Dependencies** (`requirements.txt`):
   - Same as pdf_orders (FastAPI, Celery, Anthropic, psycopg, etc.)

3. **Database**:
   - Use same tables (no schema changes needed)
   - Verify connection works

4. **Documentation**:
   - Create `README.md` with setup instructions
   - Create `Docs/Communication.md` for change tracking

## File Structure
```
text_orders/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── celery_app.py
│   ├── database.py
│   ├── models.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── task_fetch_emails.py
│   │   ├── task_extract_emails.py  # NEW - replaces manual Claude Code
│   │   ├── task_extract_data.py
│   │   └── task_tidy_emails.py
│   ├── subagents/  # Copy from pdf_orders
│   ├── prompts/   # Copy from pdf_orders
│   └── utils/      # Copy from pdf_orders
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── api/
│   │   ├── hooks/
│   │   └── types/
│   └── package.json
├── temp/           # Runtime directory
├── requirements.txt
├── .env
└── README.md
```

## Key Implementation Details

### Task 2: Email Extraction Prompt
Convert `TEXT_ORDERS_PROMPT.md` logic into Anthropic API prompt:
- Input: Raw email thread from `emails_raw.json`
- Output: JSON with `original_email` (from, subject, date, footer) and `full_thread_body`
- Use Anthropic Messages API (text-only, no vision needed)

### Task 3: CSV Conversion
Before subagent processing, convert `emails_extracted.json` to CSV format:
- Format matches `finalize_text_orders.py` output
- Sections: EMAIL HEADER, EMAIL BODY, EMAIL FOOTER, ENTRY ID
- Single column CSV (Column A = full formatted email text)

### Folder Paths
- Source: `Inbox/FD/WIP_Text_Orders`
- Destination: `Inbox/FD/ProcessedOrders_Text_Orders`
- Desktop export: `~/Desktop/ProcessedEmails/YYYY-MM-DD/`

## Testing Considerations
- Test email extraction with various forwarded thread formats
- Verify Spanish character handling (UTF-8 encoding)
- Test subagent extraction with text email format
- Verify database insertion matches pdf_orders behavior
- Test email categorization and folder movement

## Notes
- All database operations use same tables/columns as pdf_orders
- Subagents are identical (no changes needed)
- Frontend is separate app but similar UX to pdf_orders
- Task 2 is the key differentiator (automated email extraction vs manual Claude Code)

