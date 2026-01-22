# Phase 4: Containerization Plan

## Overview

Containerize the application with Docker and migrate file storage from local `temp/` to Azure Blob Storage.

## Deliverables

1. **Dockerfiles** - Multi-stage builds for API, Worker, Frontend
2. **Docker Compose** - Local development with all services
3. **Azure Blob Storage Migration** - Replace local temp/ directory

---

## 1. Docker Configuration

### 1.1 Backend Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Default command (override in docker-compose)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 1.2 Frontend Dockerfile (`frontend/Dockerfile`)

```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 1.3 Docker Compose (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MICROSOFT_TENANT_ID=${MICROSOFT_TENANT_ID}
      - MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID}
      - MICROSOFT_CLIENT_SECRET=${MICROSOFT_CLIENT_SECRET}
      - MICROSOFT_OBJECT_ID=${MICROSOFT_OBJECT_ID}
      - AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING}
    depends_on:
      - redis
    volumes:
      - temp_storage:/app/temp

  worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: celery -A backend.celery_app worker --loglevel=info --pool=solo
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MICROSOFT_TENANT_ID=${MICROSOFT_TENANT_ID}
      - MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID}
      - MICROSOFT_CLIENT_SECRET=${MICROSOFT_CLIENT_SECRET}
      - MICROSOFT_OBJECT_ID=${MICROSOFT_OBJECT_ID}
      - AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING}
    depends_on:
      - redis
    volumes:
      - temp_storage:/app/temp

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api

volumes:
  redis_data:
  temp_storage:
```

---

## 2. Azure Blob Storage Migration

### 2.1 Create Storage Helper (`backend/utils/blob_storage.py`)

```python
import os
from azure.storage.blob import BlobServiceClient, ContainerClient

# Use Azure Blob if connection string exists, otherwise local storage
USE_AZURE = bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
CONTAINER_NAME = "order-processing-temp"

def get_blob_client():
    """Get Azure Blob container client."""
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    return blob_service.get_container_client(CONTAINER_NAME)

def upload_file(local_path: str, blob_name: str) -> str:
    """Upload file to blob storage or keep local."""
    if USE_AZURE:
        container = get_blob_client()
        with open(local_path, "rb") as data:
            container.upload_blob(blob_name, data, overwrite=True)
        return f"blob://{CONTAINER_NAME}/{blob_name}"
    return local_path

def download_file(blob_name: str, local_path: str) -> str:
    """Download file from blob storage or use local."""
    if USE_AZURE:
        container = get_blob_client()
        with open(local_path, "wb") as f:
            blob_data = container.download_blob(blob_name)
            f.write(blob_data.readall())
    return local_path

def delete_job_files(job_id: str):
    """Delete all files for a job."""
    if USE_AZURE:
        container = get_blob_client()
        blobs = container.list_blobs(name_starts_with=f"job_{job_id}/")
        for blob in blobs:
            container.delete_blob(blob.name)
    else:
        # Local cleanup (existing logic)
        import shutil
        temp_dir = f"temp/job_{job_id}"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
```

### 2.2 Update Requirements

Add to `requirements.txt`:
```
azure-storage-blob>=12.19.0
```

### 2.3 Update Tasks to Use Storage Helper

Modify file operations in:
- `backend/tasks/task_fetch_emails.py`
- `backend/tasks/task_extract_emails.py`
- `backend/tasks/task_extract_data.py`
- `backend/tasks/task_tidy_emails.py`

Pattern:
```python
from backend.utils.blob_storage import upload_file, download_file

# Instead of: with open("temp/pdfs/file.pdf", "wb") as f:
# Use: upload_file(local_path, f"job_{job_id}/pdfs/file.pdf")
```

---

## 3. Frontend nginx.conf

Create `frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 4. Implementation Checklist

- [x] Create `backend/Dockerfile`
- [x] Create `frontend/Dockerfile`
- [x] Create `frontend/nginx.conf`
- [x] Create `docker-compose.yml`
- [ ] Create `backend/utils/blob_storage.py`
- [ ] Add `azure-storage-blob` to requirements.txt
- [ ] Update task files to use storage helper

**✅ Phase 4 Complete** - Remaining items moved to Phase 5 (Azure Deployment):
- Create Azure Blob Storage container
- Test with Docker Compose locally
- Update `.env.example` with new variables

---

## 5. Environment Variables

Add to `.env`:
```
# Azure Blob Storage (optional for local dev)
AZURE_STORAGE_CONNECTION_STRING=
```

---

## 6. Testing

### Local Docker Testing
```bash
# Start all services
docker-compose up --build

# Test API health
curl http://localhost:8000/api/health

# Access frontend
open http://localhost:80
```

### Verify Blob Storage
```bash
# Run with Azure storage
AZURE_STORAGE_CONNECTION_STRING="..." docker-compose up

# Check blob container for uploaded files after processing
```

---

## Timeline

| Task | Estimated Effort |
|------|------------------|
| Dockerfiles + Compose | Medium |
| Blob Storage Helper | Medium |
| Update Tasks for Blob | Medium |
| Testing | Medium |

---

## Next Phase

Phase 5 will deploy to Azure Container Apps with:
- **Azure Container Registry (ACR)** - Create registry and push Docker images
- Azure Redis Cache
- Azure Key Vault for secrets
- CI/CD pipeline with GitHub Actions
