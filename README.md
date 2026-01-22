# Text Order Processing Web Application

A web-based system for automated text order processing from email threads, featuring email extraction, data validation, and database integration.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Redis server running on localhost:6379
- PostgreSQL database with required tables

### Environment Setup

1. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Start Services

**Backend (FastAPI + Celery):**
```bash
# Terminal 1: Start FastAPI server
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Start Celery worker
celery -A backend.celery_app worker --loglevel=info
```

**Frontend:**
```bash
# Terminal 3: Start React dev server
cd frontend
npm run dev
```

Then open your browser to: **http://localhost:5173**

## 📖 Project Structure

```
text_orders/
├── backend/              # FastAPI + Celery Backend
│   ├── main.py          # REST API endpoints
│   ├── tasks/           # 4 Celery tasks
│   │   ├── task_fetch_emails.py
│   │   ├── task_extract_emails.py  # NEW - replaces manual Claude Code
│   │   ├── task_extract_data.py
│   │   └── task_tidy_emails.py
│   ├── subagents/       # 8 data extraction agents (copied from pdf_orders)
│   └── prompts/         # Prompt templates (copied from pdf_orders)
├── frontend/            # React + TypeScript Frontend
│   └── src/
│       ├── api/         # API client
│       ├── components/  # React components
│       ├── hooks/       # Custom hooks
│       └── types/       # TypeScript definitions
├── temp/                # Runtime directory (created automatically)
├── Docs/                # Documentation
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🔄 Complete Workflow

1. User clicks "Process Orders" → Job created
2. **Task 1:** Fetch Emails → Fetches text-only emails from Outlook `WIP_Text_Orders` folder
3. **Task 2:** Extract Emails → Uses Anthropic API to extract original emails from forwarded threads
4. **Task 3:** Data Extraction → 8 subagents extract structured data
5. **⏸️ Pause Point** → User reviews extracted orders → Approves
6. **Task 4:** Email Tidying → Categorizes, exports, and archives emails
7. **Job Complete** → User downloads CSV results

## 🛠️ Tech Stack

**Backend:** FastAPI, Celery, Redis, PostgreSQL, Anthropic API (Claude Sonnet 4.5)
**Frontend:** React 18, TypeScript, Vite, TanStack Query, Tailwind CSS
**Integration:** Microsoft Graph API (Email)

## 📊 API Endpoints

- `GET /` - Health check
- `POST /api/jobs/start` - Create new job
- `GET /api/jobs/{id}/status` - Get job progress
- `GET /api/jobs/{id}/preview` - Get extracted data (Pause Point)
- `POST /api/jobs/{id}/approve` - Approve data
- `GET /api/jobs/{id}/results` - Download CSVs
- `GET /api/prompts/{name}` - Get prompt file content
- `GET /api/health` - Comprehensive health check

Interactive API docs: **http://localhost:8000/docs**

## 🔑 Environment Variables

Required environment variables (see `.env.example`):

```
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic API
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_MODEL_DEFAULT=claude-sonnet-4-5-20250929
ANTHROPIC_MODEL_COMPLEX=claude-sonnet-4-5-20250929

# Microsoft Graph API
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_OBJECT_ID=your-user-object-id
```

## 📈 Key Differences from PDF Orders

- **No OCR**: Text emails don't need PDF processing
- **Email Extraction**: Task 2 extracts original emails from forwarded threads (replaces manual Claude Code step)
- **Folder Paths**: `WIP_Text_Orders` → `ProcessedOrders_Text_Orders` (vs PDF folders)
- **Input Format**: Raw email threads (vs PDF attachments)

## 🐛 Troubleshooting

**Common Issues:**

- **Port already in use?** → Change port in uvicorn command or kill existing process
- **Redis not running?** → Start Redis server: `redis-server`
- **Database connection error?** → Check DATABASE_URL in `.env`
- **Microsoft Graph API error?** → Verify credentials and permissions

## 📞 Service URLs

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Redis:** localhost:6379

