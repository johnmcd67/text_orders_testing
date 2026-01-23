# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Text Order Processing Web Application - automated system for processing text-based customer orders from email threads. The system fetches emails from Outlook, extracts structured data using AI (Claude Sonnet 4.5), validates against PostgreSQL database, and provides a user review checkpoint before final database integration.

**Tech Stack:**
- Backend: FastAPI + Celery + Redis + PostgreSQL + Anthropic API
- Frontend: React 19 + TypeScript + Vite + TanStack Query + Tailwind CSS
- Integration: Microsoft Graph API (O365 email)

## Development Commands

### Start Development Environment (3 Terminals Required)

Terminal 1 - FastAPI Server:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

Terminal 2 - Celery Worker:
```bash
celery -A backend.celery_app worker --loglevel=info
```

Terminal 3 - Frontend Dev Server:
```bash
cd frontend
npm run dev
```

**Service URLs:**
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Frontend Commands
```bash
npm run build      # TypeScript compile + Vite build for production
npm run lint       # Run ESLint
npm run preview    # Preview production build locally
```

### Initial Setup
```bash
cp .env.example .env              # Configure environment variables
pip install -r requirements.txt   # Install Python dependencies
cd frontend && npm install        # Install frontend dependencies
```

## Core Architecture

### 4-Task Sequential Workflow with Pause Point

The system uses Celery task chaining for sequential processing with a mandatory user review checkpoint:

**Task 1: Fetch Emails** (`backend/tasks/task_fetch_emails.py`)
- Connects to Microsoft Graph API
- Fetches emails from `Inbox/FD/WIP_Text_Orders` folder
- Saves raw email data to `temp/emails_raw.json`
- Auto-chains to Task 2

**Task 2: Extract Emails** (`backend/tasks/task_extract_emails.py`)
- Processes forwarded email threads
- Uses Claude API to extract original email from thread (header, body, footer)
- Saves cleaned emails to `temp/emails_cleaned.json`
- Auto-chains to Task 3

**Task 3: Extract Data** (`backend/tasks/task_extract_data.py`)
- Runs 8 subagents sequentially for each email (see Subagent Architecture below)
- Generates `temp/order_details.csv` with extracted data
- Sets job status to `awaiting_review_data`
- **STOPS HERE - waits for user approval**

**Pause Point: User Review**
- Frontend displays extracted orders in DataReviewTable component
- User can edit/approve/reject data
- POST `/api/jobs/{id}/approve` resumes workflow to Task 4

**Task 4: Tidy Emails** (`backend/tasks/task_tidy_emails.py`)
- Inserts approved orders to PostgreSQL (`testing.ai_tool_input_table_from_web_app`)
- Exports email files (.eml) to Azure File Share (instantly accessible via W: drive)
- Updates `email_directory` field in `ai_tool_output_table` with file path
- Categorizes processed emails as Green in Outlook
- Moves emails from WIP_Text_Orders to ProcessedOrders_Text_Orders folder
- Marks job as `completed`

### Subagent Architecture (8 Specialized Agents)

Each subagent in `backend/subagents/` is an independent module that processes email text and returns structured data:

1. **customer_id.py** - Extract customer name + fuzzy match against `public.clients` table (RapidFuzz, 60% threshold)
2. **sku_extraction.py** - Extract product SKU (13-digit format) + quantity from order text
3. **reference_no.py** - Extract purchase order/reference number
4. **valve_detection.py** - Detect if valve is requested (yes/no)
5. **delivery_address.py** - Extract delivery address (fuzzy match against known customer addresses)
6. **cpsd_extraction.py** - Extract CPSD (Confirmed Plan Ship Date)
7. **options_extraction.py** - Extract optional items/accessories
8. **db_export.py** - Insert validated data to PostgreSQL

**Prompt Templates:** All subagents use prompt files in `backend/prompts/` (e.g., `customer_id.txt`, `sku_extraction.txt`, `failure_summary.txt`)

**Execution Pattern:** Customer ID runs first, then other subagents run in parallel using ThreadPoolExecutor for efficiency.

### Utility Modules

- `backend/utils/database.py` - DatabaseHelper class for PostgreSQL operations
- `backend/utils/anthropic_helper.py` - AnthropicHelper with retry logic for Claude API
- `backend/utils/blob_storage.py` - Azure Blob Storage for temp files (cloud deployment)
- `backend/utils/azure_file_share.py` - Azure File Share for email export (accessible via W: drive)
- `backend/utils/pdf_generator.py` - Generate PDF reports for failure summaries

### Local Scripts

- `scripts/export_emails_to_w_drive.py` - Local script to export emails to W: drive when email_directory is NULL (run manually when needed)

### Database Architecture

**Key Tables:**

`public.job_runs` - Job tracking
- id, status (pending/running/awaiting_review_data/completed/failed), progress (0-100%), progress_message
- created_at, completed_at, number_of_orders, number_of_order_lines

`testing.ai_tool_input_table_from_web_app` - Input staging table for orders
- orderno, customerid, 13DigitAlias (SKU), orderqty, reference_no, valve, delivery_address, alternative_cpsd, entry_id, option_sku, option_qty, telephone_number, contact_name, order_type, job_id

`public.ai_tool_output_table` - Final output table with all order details (40+ fields)
- Includes `email_id` (original email ID from Outlook) and `email_directory` (path to exported .eml file)

`public.AI_Tool_OutputTable_v2` - Pre-formatted view for reporting

**Database Patterns:**
- Use `DatabaseHelper` class (`backend/utils/database.py`) with context manager pattern
- Always use prepared statements (psycopg parameterized queries) to prevent SQL injection
- Use `insert_orders_batch()` for multi-row INSERT to trigger database triggers correctly
- Fuzzy matching uses RapidFuzz `token_set_ratio` for partial/reordered word matches
- Connection pooling handled by DatabaseHelper singleton (`get_db_helper()`)

### Frontend Architecture

**Component Structure:**
- `LandingPage.tsx` - Home page with 3 main action buttons
- `Dashboard.tsx` - Main job processing workflow UI
- `DataReviewTable.tsx` - **Critical: User review pause point UI** (editable table)
- `FailureSummaryPanel.tsx` - AI-generated analysis of failed orders with PDF export
- `History.tsx` - Job history + analytics charts (Recharts)
- `ViewPrompts.tsx` - View/edit prompt templates
- `components/ui/` - 13 Shadcn UI components (Radix UI + Tailwind)

**State Management:**
- TanStack Query (React Query) for all server state
- `useJobPolling` hook: Polls job status every 2 seconds during processing
- Status-based refetch intervals: Fast polling during `running`, slower during `awaiting_review_data`

**API Client:**
- `frontend/src/api/jobsApi.ts` - 11 endpoint methods (start, status, preview, approve, results, history, orders history, order-lines history, avg process time, failure summary, failure summary PDF)
- Axios with proxy to localhost:8000 (configured in `vite.config.ts`)

**Routing:**
- React Router v7 with 4 routes: `/`, `/order-processing`, `/history`, `/view-prompts`

## Critical Patterns and Conventions

### Celery Task Chaining
Tasks use immutable signatures for auto-chaining:
```python
from celery import chain
chain(task_extract_emails.si(job_id), task_extract_data.si(job_id)).apply_async()
```
Never use `.delay()` or `.apply_async()` with args in chain - use `.si()` (immutable signature).

### Error Handling
- Failed orders logged with detailed messages to `backend/logs/`
- Failed orders exported separately to `failed_orders.csv`
- Job can fail at any stage - status updates to `failed` with error in `progress_message`
- Database operations wrapped in try/except with rollback on failure

### Fuzzy Matching Rules
- Customer name matching: 60% threshold, uses `fuzz.token_set_ratio`
- Hardcoded mappings in `customer_id.py` for known edge cases (NEWKER, FERROLAN->ALANTA, etc.)
- Address matching: Fuzzy match against `v_md_clients_addresses` view for known customer

### Multi-line Order Support
- Single email can contain multiple product lines
- Each line creates separate order record with same `orderno` but different `entry_id`
- Orders grouped by `orderno` for display in frontend

### API Rate Limiting
- `AnthropicHelper` (`backend/utils/anthropic_helper.py`) includes exponential backoff retry logic
- Max retries: 3, backoff factor: 2 (waits 2s, 4s, 8s)
- Handles 429 (rate limit) and 500 (server error) responses

### File Paths
- All temp files go to `temp/` directory (created at runtime if missing)
- Email archive paths use forward slashes even on Windows
- Microsoft Graph API folder paths are case-insensitive

## Environment Variables

Required in `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# Redis/Celery
# Local: redis://localhost:6379/0
# Azure: rediss://:<key>@<host>.redis.cache.windows.net:6380/0
REDIS_URL=redis://localhost:6379/0

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_DEFAULT=claude-sonnet-4-5-20250929
ANTHROPIC_MODEL_COMPLEX=claude-sonnet-4-5-20250929

# Microsoft Graph API (O365)
MICROSOFT_TENANT_ID=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_OBJECT_ID=...

# Azure File Share (for email export to mapped network drive)
AZURE_STORAGE_ACCOUNT=fdorderprocessingstorage
AZURE_FILE_SHARE=fdorderprocessingfileshare
AZURE_STORAGE_KEY=...

# Azure Blob Storage (for temp file storage in cloud deployment)
AZURE_STORAGE_CONNECTION_STRING=...

# Authentication
JWT_SECRET=your-secret-key-here
```

## Key Configuration Files

- `backend/celery_app.py` - Celery config (1 hour task timeout, JSON serialization, UTC timezone)
- `frontend/vite.config.ts` - Dev server port 5173, API proxy to :8000, React plugin
- `frontend/tsconfig.app.json` - TypeScript strict mode, ES2022 target, path aliases (`@/*` -> `./src/*`)
- `frontend/tailwind.config.js` - Dark mode, custom animations, Shadcn theme

## Key Features

### Failure Summary Analysis
- AI-powered analysis of failed orders using Claude API
- Cached summaries stored in database (`failure_summary`, `failure_summary_generated_at` columns in `job_runs`)
- Regenerate on demand via `?regenerate=true` query param
- PDF export via `backend/utils/pdf_generator.py` (uses WeasyPrint)
- Frontend: `FailureSummaryPanel.tsx` with collapsible markdown rendering

### Email Export to Azure File Share
- Processed emails exported as .eml files to Azure File Share
- Files prefixed with `TEXT_` to distinguish from PDF orders
- Date folders: `YYMMDD_test` format
- Accessible locally via mapped W: drive at `W:\PEDIDOS Y ALBARANES\PEDIDOS DIGITAL\`
- Path stored in `ai_tool_output_table.email_directory`

## Common Development Tasks

### Adding a New Subagent
1. Create new file in `backend/subagents/your_agent.py`
2. Create prompt file in `backend/prompts/your_agent.txt`
3. Add function call in `task_extract_data.py` in appropriate execution order
4. Update frontend TypeScript types in `frontend/src/types/job.types.ts` if new fields added
5. Update DataReviewTable component to display new field

### Modifying Prompts
- Prompts are in `backend/prompts/` as `.txt` files
- Can be viewed/edited via frontend: `/view-prompts` route
- API endpoint: `GET /api/prompts/{name}` (e.g., `/api/prompts/customer_id`)
- Changes take effect immediately (no restart required)

### Database Changes
- Schema files documented in `postgres_schema/` (4 files)
- Use DatabaseHelper methods for queries - never raw SQL strings
- Test fuzzy matching queries with `fuzzy_match_customer()` method
- Batch inserts must use `insert_orders_batch()` for trigger compatibility

### Testing Locally
1. Ensure Redis is running: `redis-cli ping` (should return PONG)
2. Check database connection: Visit http://localhost:8000/api/health
3. Test email connection: Verify Microsoft Graph credentials in `.env`
4. Monitor Celery tasks: Watch Terminal 2 for task logs
5. Check frontend API calls: Browser DevTools Network tab
6. Test Azure File Share: Ensure W: drive is mapped and accessible
7. Run local email export: `python scripts/export_emails_to_w_drive.py`

## Debugging Tips

### Celery Task Failures
- Check `backend/logs/` for detailed error logs
- Verify Redis connection: Task won't queue if Redis is down
- Check task timeout (1 hour max) - long-running tasks may timeout
- Use `job_runs.progress_message` field for user-facing error info

### Frontend Polling Issues
- `useJobPolling` hook stops polling if job status is terminal (`completed` or `failed`)
- Polling interval: 2 seconds during active processing
- If job stuck in `running` state, check Celery worker logs

### Database Fuzzy Match Not Working
- Verify `public.clients` table has data
- Check threshold (0.6 = 60% similarity) - may need adjustment
- Test with `DatabaseHelper.fuzzy_match_customer()` method directly
- Add hardcoded mapping in `customer_id.py` for persistent edge cases

### Email Fetching Failures
- Verify Microsoft Graph API credentials in `.env`
- Check folder path: `Inbox/FD/WIP_Text_Orders` (case-insensitive)
- Test authentication with Graph Explorer: https://developer.microsoft.com/en-us/graph/graph-explorer
- Ensure user object ID matches mailbox owner

### Azure File Share Issues
- Verify credentials: `AZURE_STORAGE_ACCOUNT`, `AZURE_FILE_SHARE`, `AZURE_STORAGE_KEY`
- Check W: drive mapping if running locally
- Email ID matching: DB stores Base64 IDs (+/), Graph API uses URL-safe (-_)
- Use `normalize_email_id()` for comparison between DB and Graph API IDs

## Related to PDF Orders Codebase

This codebase is a sibling project to the PDF Orders application. Key differences:
- No OCR processing (text emails vs PDF attachments)
- Task 2 (Extract Emails) replaces manual Claude Code step from PDF workflow
- Different folder paths: `WIP_Text_Orders` vs `WIP_PDF_Orders`
- Shared database schema and subagent logic (copied from pdf_orders)
- Same 8 subagent architecture for data extraction

When making changes that affect core logic (subagents, prompts, database schema), consider if the PDF Orders codebase needs the same updates.
