# Web App Architecture Plan

## Source Projects

This web app consolidates three existing projects:

1. **Current Project (PDF Email Processing)**
   - Location: `C:\Users\AI_USER\Desktop\Order Processing\pdf_orders`
   - Purpose: Fetches PDF orders from Outlook, extracts content via Claude Code OCR
   - Key files: `process_orders.py`, `finalize_orders.py`, `PDF_OCR_EXTRACTION_PROMPT.md`

2. **Project 1 (Data Extraction & Database Insert)**
   - Location: `C:\Users\AI_USER\Desktop\Scripts\FD_OrderIntake_PDFs_Anthropic`
   - Purpose: Orchestrator with 8 subagents extracts structured data, inserts into PostgreSQL
   - Key files: `main.py`, `customer_id.py`, `sku_extraction.py`, `db_export.py`, etc.

3. **Project 2 (Email Tidying)**
   - Location: `C:\Users\AI_USER\Desktop\Scripts\ExportEmailFromInbox`
   - Purpose: Categorizes emails as green, moves to archive folder, updates database
   - Key files: `export_processed_emails_to_desktop_folder_PDF.py`

## Tech Stack
- **Backend**: FastAPI (Python) - async support, fast, modern
- **Frontend**: React - dashboard with progress tracking
- **Job Queue**: Celery + Redis - async processing for 200+ PDFs
- **Database**: PostgreSQL (existing)
- **API**: Anthropic API (Claude Sonnet 4.5) - replaces Claude Code
- **Container**: Docker multi-stage build
- **Azure**: Container Apps or Web App for Containers
- **Storage**: Azure Blob Storage (temp PDFs/CSVs during processing)

## Architecture Components

### 1. Frontend (React)
- "Process Orders" button to trigger workflow
- Job status dashboard (Step 1/3: Fetching emails... Step 2/3: OCR processing 47/200...)
- **Review UI** - Shows extracted data from output_cleaned.csv before DB insert
- Approve/Reject buttons to proceed with data insertion
- Error handling UI (failed PDFs, retry options)
- Download output_cleaned.csv and order_details.csv

### 2. Backend API (FastAPI)
- `/api/jobs/start` - Trigger new processing job
- `/api/jobs/{id}/status` - Get job progress
- `/api/jobs/{id}/preview` - Get extracted data for review
- `/api/jobs/{id}/approve` - Proceed with DB insertion after review
- `/api/jobs/{id}/results` - Download CSVs

### 3. Worker Service (Celery)
- **Task 1**: Fetch emails + download PDFs (process_orders.py logic)
- **Task 2**: OCR PDFs with Anthropic API (replaces Claude Code step)
- **Task 3**: Extract data with orchestrator/subagents (Project 1)
- **Task 4**: Categorize/move emails (Project 2)
- Progress tracking with Redis

### 4. Database Layer
- Standardize on `psycopg` (v3) for all connections
- Existing tables: `ai_tool_input_table_from_web_app`, `ai_tool_output_table`
- Job tracking table: `job_runs` (id, status, progress, created_at, completed_at)

## Workflow Sequence
1. User clicks "Process Orders" → Job created in DB
2. Worker fetches emails from Outlook → saves to Blob Storage
3. Worker calls Anthropic API for each PDF (vision OCR) → generates output_cleaned.csv
4. **PAUSE** - Job status = "awaiting_review"
5. Frontend polls `/api/jobs/{id}/preview` → displays extracted data
6. User reviews → clicks "Approve"
7. Worker runs orchestrator + subagents → inserts into ai_tool_input_table_from_web_app
8. Database trigger fires → populates ai_tool_output_table
9. Worker categorizes emails green, moves to folder, updates email_directory
10. Job complete → User downloads CSVs

## Code Migration Strategy

### Current Project (PDF Orders)
- Extract `process_orders.py` logic → Celery task
- Replace "paste prompt to Claude Code" → Direct Anthropic API call with vision
- Extract `finalize_orders.py` logic → Celery task

### Project 1 (Orchestrator)
- Keep orchestrator + 8 subagents as-is
- Wrap in Celery task with progress tracking
- Change: Read from Blob Storage instead of local CSV

### Project 2 (Email Tidying)
- Keep Microsoft Graph API logic as-is
- Wrap in Celery task
- Trigger after Project 1 completes

## Azure Deployment

### Option A: Azure Container Apps (Recommended)
- Microservices-friendly, auto-scaling
- Separate containers: API, Worker, Frontend
- Built-in Redis integration
- Cost-effective for variable workloads

### Option B: Azure Web App for Containers
- Simpler, single container deployment
- Good for monolithic apps
- Less flexible scaling

### Supporting Azure Services:
- Azure Database for PostgreSQL (or keep existing DB)
- Azure Blob Storage (temporary file storage)
- Azure Redis Cache (Celery broker)
- Azure Key Vault (API keys, DB credentials)
- Azure Container Registry (Docker images)

## Environment Variables (Azure Key Vault)
- `ANTHROPIC_API_KEY`
- `DATABASE_URL` (PostgreSQL connection)
- `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_OBJECT_ID`
- `AZURE_STORAGE_CONNECTION_STRING`
- `REDIS_URL`

## Implementation Phases

### Phase 1: Backend Core (Week 1-2) ✓ IN PROGRESS
**See [PHASE_1_PLAN.md](PHASE_1_PLAN.md) for detailed implementation instructions**

**Deliverables:**
- FastAPI skeleton with ALL 5 endpoints:
  - `POST /api/jobs/start` - Create job, trigger Celery task chain
  - `GET /api/jobs/{id}/status` - Get job progress
  - `GET /api/jobs/{id}/preview` - Get extracted CSV data for review
  - `POST /api/jobs/{id}/approve` - Proceed with DB insertion
  - `GET /api/jobs/{id}/results` - Download CSVs
- Celery configuration with Redis broker
- **FULL implementation**: Task 2 (OCR with Anthropic Vision API)
- **STUB implementations**: Tasks 1, 3, 4 (completed in Phase 2)
- Database setup script for `job_runs` table + sequence
- Test script for 2 sample emails from Outlook
- **Local file storage** using `temp/` directory (auto-created/deleted)

**Development Environment Setup:**
- Redis for Windows (local): https://github.com/tporadowski/redis/releases
- `.env` updated with `REDIS_URL=redis://localhost:6379`
- PostgreSQL: Existing IBM Cloud database

### Phase 2: Integration (Week 2-3)
- **Complete Task 1**: Integrate `process_orders.py` logic (email fetching)
- **Complete Task 3**: Integrate Project 1 orchestrator (8 subagents, data extraction)
- **Complete Task 4**: Integrate Project 2 email tidying (categorize, move, update DB)
- Implement review/approval workflow with `awaiting_review` status
- Full end-to-end testing with task chain
- Continue using **local `temp/` storage** (defer Azure Blob to Phase 4+)

### Phase 3: Frontend (Week 3-4)
- React dashboard with job status
- Review UI for extracted data
- Progress tracking visualization
- Download results

### Phase 4: Containerization (Week 4-5)
- Dockerfile for API + Worker
- Docker Compose for local testing
- Azure Container Registry setup
- **MIGRATION**: Local `temp/` → Azure Blob Storage
  - Update file I/O in all tasks
  - Environment variable: `AZURE_STORAGE_CONNECTION_STRING`

### Phase 5: Azure Deployment (Week 5-6)
- **Pre-deployment testing:**
  - Test Docker Compose locally (`docker-compose up --build`)
  - Create `.env.example` with all required variables
- **Azure setup:**
  - Create Azure Blob Storage container (`order-processing-temp`)
  - Azure Container Registry setup + push images
  - Azure Container Apps configuration
  - Azure Redis Cache setup (replace local Redis)
  - Environment variables in Key Vault
- CI/CD pipeline (GitHub Actions)
- Update `.env` / Key Vault:
  - `REDIS_URL=redis://your-app.redis.cache.windows.net:6380?ssl=true`
  - `AZURE_STORAGE_CONNECTION_STRING=<production_value>`

### Phase 6: Testing & Optimization (Week 6-7)
- End-to-end testing with 200+ orders
- Performance optimization
- Error handling refinement
- Cost optimization

---

## Deferred Items & Migration Timeline

### Local Development (Phases 1-3)
**File Storage:** Using local `temp/` directory (existing pattern from `process_orders.py`)
- `temp/pdfs/` - Downloaded PDF attachments
- `temp/emails_data.json` - Email metadata
- `temp/ocr_results.json` - OCR output from Anthropic Vision API
- Auto-created at runtime, auto-deleted after job completion

**Redis:** Local Redis for Windows (development)
- Download: https://github.com/tporadowski/redis/releases
- Connection: `redis://localhost:6379`

### Production Migration (Phases 4-5)
**File Storage → Azure Blob Storage:**
- Create container: `order-processing-temp`
- Update all file I/O operations to use Azure SDK
- Benefits: Scalability, persistence across container restarts

**Redis → Azure Redis Cache:**
- Create managed Redis instance in Azure Portal
- Update `REDIS_URL` in environment variables
- Benefits: Managed service, high availability, no maintenance

**No code logic changes required** - only environment variable updates and file I/O adapters.

---

## Key Changes to Existing Code

### Phase 1 Changes:
1. **Add Anthropic Vision API**: Replace manual Claude Code OCR step with automated API calls
2. **Database**: Create `job_runs` table for tracking job status/progress
3. **Celery tasks**: Wrap existing logic in task decorators (Task 2 fully implemented, others stubbed)

### Phase 2 Changes:
1. **Standardize DB driver**: Ensure all code uses `psycopg` (v3) - Project 2 already uses this
2. **Wrap in Celery tasks**: Complete Tasks 1, 3, 4 integration
3. **Add progress tracking**: Emit progress updates from workers to `job_runs` table
4. **Environment variables**: Unify naming conventions across all 3 projects

### Phase 4-5 Changes:
1. **File paths**: Replace local `temp/` paths → Azure Blob Storage paths
2. **Redis URL**: Update to point to Azure Redis Cache
3. **Container configuration**: Add health checks, scaling rules

## Estimated Costs (Azure)
- Container Apps: ~$50-100/month (small scale)
- PostgreSQL: ~$30-50/month (basic tier)
- Blob Storage: ~$5-10/month
- Redis Cache: ~$15-30/month (basic tier)
- Anthropic API: ~$150-300/month (200 PDFs/day)
- **Total: ~$250-500/month**
