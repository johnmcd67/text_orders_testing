# Text Order Processing Web Application

A web-based system for automated text order processing from email threads, featuring email extraction, data validation, and database integration.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Redis for Windows
- PostgreSQL database

### Start All Services

From the project root directory:

```powershell
.\terminal_checks\start_services.ps1
```

Or from within this folder:

```powershell
cd terminal_checks
.\start_services.ps1
```

Then open your browser to: **http://localhost:5173**

### Stop All Services

```powershell
.\terminal_checks\stop_services.ps1
```

Or from within this folder:

```powershell
cd terminal_checks
.\stop_services.ps1
```

## 📖 Documentation

- **[SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md)** - Complete guide for starting/stopping services
- **[IMPLEMENTATION_PLAN.md](../Docs/IMPLEMENTATION_PLAN.md)** - Overall architecture and implementation plan
- **[Communication.md](../Docs/Communication.md)** - Implementation details and change log

## 🏗️ Project Structure

```
text_orders/
├── backend/                    # FastAPI + Celery Backend
│   ├── main.py                # FastAPI application
│   ├── celery_app.py          # Celery configuration
│   ├── database.py            # PostgreSQL operations
│   ├── models.py             # Pydantic models
│   ├── tasks/                 # 4 Celery tasks
│   │   ├── task_fetch_emails.py      # Task 1: Email fetching (Microsoft Graph)
│   │   ├── task_extract_emails.py    # Task 2: Extract original emails (Anthropic API)
│   │   ├── task_extract_data.py      # Task 3: Data extraction (8 subagents)
│   │   └── task_tidy_emails.py       # Task 4: Email categorization & archiving
│   └── subagents/             # 8 data extraction subagents
├── frontend/                   # React + TypeScript Frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom hooks (polling)
│   │   └── types/             # TypeScript definitions
│   └── package.json
├── postgres_schema/           # Database schema
├── Docs/                      # Documentation
├── terminal_checks/           # 🆕 Service management scripts
│   ├── start_services.ps1         # Smart service starter
│   ├── stop_services.ps1          # Service shutdown script
│   ├── check_status.ps1           # Status checker with menu
│   ├── SERVICE_MANAGEMENT.md      # Service management guide
│   └── README.md                  # This file
└── requirements.txt           # Python dependencies
```

## 🔄 Complete Workflow

1. **User clicks "Process Orders"** → Job created
2. **Task 1: Fetch Emails** → Fetches text-only emails from Outlook `WIP_Text_Orders` folder
3. **Task 2: Extract Emails** → Uses Anthropic API to extract original emails from forwarded threads
4. **Task 3: Data Extraction** → 8 subagents extract structured data
5. **⏸️ Pause Point** → User reviews extracted orders → Approves
6. **Task 4: Email Tidying** → Categorizes, exports, and archives emails
7. **Job Complete** → User downloads CSV results

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Async REST API
- **Celery** - Async task queue
- **Redis** - Message broker
- **PostgreSQL** - Database
- **Anthropic API** - Claude Sonnet 4.5 for email extraction
- **Microsoft Graph API** - Email integration

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TanStack Query** - Server state & polling
- **Tailwind CSS** - Styling
- **Axios** - HTTP client

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/jobs/start` | Create new job |
| GET | `/api/jobs/{id}/status` | Get job progress |
| GET | `/api/jobs/{id}/preview` | Get extracted data (Pause Point) |
| POST | `/api/jobs/{id}/approve` | Approve data, start email tidying |
| GET | `/api/jobs/{id}/results` | Download CSV results |
| GET | `/api/prompts/{name}` | Get prompt file content |
| GET | `/api/health` | Comprehensive health check |

## 🔐 Configuration

Create a `.env` file with:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
DATABASE_URL=postgresql://user:pass@host:port/dbname
MICROSOFT_TENANT_ID=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_OBJECT_ID=...
REDIS_URL=redis://localhost:6379
```

## 🧪 Testing

### Manual Testing
1. Start all services: `.\terminal_checks\start_services.ps1`
2. Open browser: http://localhost:5173
3. Click "Process Orders"
4. Follow the workflow through the review point
5. Download CSV results

### API Testing
Access interactive API docs: http://localhost:8000/docs

## 🐛 Troubleshooting

### Port Already in Use
```powershell
# The start script handles this automatically!
.\terminal_checks\start_services.ps1
```

### Services Not Starting
See [SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md#-troubleshooting)

### Redis Connection Errors
```powershell
# Check if Redis is running
Get-Process redis-server

# Install/start Redis service
redis-server --service-install
redis-server --service-start
```

## 🚀 Development Workflow

### Starting Your Day
```powershell
.\terminal_checks\start_services.ps1
# All services start automatically, open http://localhost:5173
```

### Making Changes
- **Backend changes** → FastAPI auto-reloads
- **Frontend changes** → Vite auto-reloads
- **Celery task changes** → Restart Celery worker manually

### Ending Your Day
```powershell
.\terminal_checks\stop_services.ps1
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [React Documentation](https://react.dev/)
- [TanStack Query Documentation](https://tanstack.com/query/latest)
- [Anthropic API Documentation](https://docs.anthropic.com/)

## 🤝 Contributing

1. Follow the existing code structure
2. Use TypeScript for frontend code
3. Add type hints for Python code
4. Test thoroughly before committing
5. Update documentation as needed

## 📝 License

Internal project - All rights reserved

## 👤 Author

AI_USER

---

**Need Help?** See [SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md) for detailed service management instructions.

