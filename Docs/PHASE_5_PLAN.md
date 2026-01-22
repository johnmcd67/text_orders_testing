# Phase 5: Azure Production Deployment

**Project:** Text Order Processing Web Application
**Phase:** 5 of 6
**Status:** READY FOR IMPLEMENTATION
**Date:** December 2025
**Duration:** Week 5-6

---

## OVERVIEW

Phase 5 deploys the Text Order Processing application to Azure Container Apps using the same proven architecture as the PDF Orders application. The deployment uses automated CI/CD via GitHub Actions, deploying three containers (Frontend, Backend, Celery Worker) with Azure Redis Cache and Azure Blob Storage.

### **Key Objectives:**
1. Provision Azure infrastructure (Container Apps, Redis Cache, Blob Storage)
2. Configure GitHub Actions CI/CD pipeline for automated deployments
3. Migrate from local Redis and temp files to Azure managed services
4. Deploy three containers with auto-scaling and health monitoring
5. Enable production-ready monitoring and rollback capabilities

### **Naming Convention:**
This deployment uses `-text` suffix naming to distinguish from the PDF Orders app:
- Resource Group: `order-processing-text-rg`
- Container Apps: `order-processing-text-frontend`, `order-processing-text-backend`, `order-processing-text-worker`
- Registry: `orderprocessingtextregistry`

### **Production URLs (after deployment):**
- **Frontend:** `https://order-processing-text-frontend.<environment>.uksouth.azurecontainerapps.io`
- **Backend:** `https://order-processing-text-backend.<environment>.uksouth.azurecontainerapps.io`
- **Backend Health:** `https://order-processing-text-backend.<environment>.uksouth.azurecontainerapps.io/api/health`

---

## ARCHITECTURE OVERVIEW

### **Infrastructure Components:**

| Component | Resource Name | Purpose | Cost (Monthly) |
|-----------|---------------|---------|----------------|
| **Resource Group** | `order-processing-text-rg` | Container for all resources | Free |
| **Container Registry** | `orderprocessingtextregistry.azurecr.io` | Docker image storage | £5 (Basic tier) |
| **Container Apps Environment** | `order-processing-text-env` | Shared environment for containers | £30-40 |
| **Azure Redis Cache** | `order-processing-text-redis` | Celery message broker | £50 (Standard tier) |
| **Azure Blob Storage** | `orderprocessingtextstorage` | Temporary file storage | £5-10 (Standard tier) |
| **IBM Cloud PostgreSQL** | External (existing) | Database (no change) | Existing cost |
| **Total Estimated Cost** | - | - | **£90-105/month** |

### **Application Stack:**

```
+-------------------------------------------------------------+
|                Azure Container Apps Environment              |
|                                                              |
|  +--------------+  +--------------+  +--------------+       |
|  |   Frontend   |  |   Backend    |  |Celery Worker |       |
|  |  React+nginx |  |   FastAPI    |  |   (Tasks)    |       |
|  |  0.25 CPU    |  |   0.5 CPU    |  |   0.5 CPU    |       |
|  |  0.5Gi RAM   |  |   1.0Gi RAM  |  |   1.0Gi RAM  |       |
|  |  1-3 replicas|  |  1-5 replicas|  |  1-3 replicas|       |
|  +------+-------+  +------+-------+  +------+-------+       |
|         |                 |                 |                |
+---------+-----------------+-----------------+----------------+
          |                 |                 |
          |                 +--------+--------+
          |                          |
    +-----v------+            +------v------+
    |   Users    |            |    Azure    |
    |  (Browser) |            |    Redis    |
    +------------+            |    Cache    |
                              +------+------+
                                     |
                              +------v------+
                              |    Azure    |
                              |    Blob     |
                              |   Storage   |
                              +------+------+
                                     |
                              +------v------+
                              | IBM Cloud   |
                              | PostgreSQL  |
                              +-------------+
```

### **Container Communication:**

| Container | Ingress Type | Exposed To | Purpose |
|-----------|--------------|------------|---------|
| **Frontend** | External | Public Internet | User interface, serves React SPA |
| **Backend** | External | Public Internet | REST API endpoints |
| **Celery Worker** | Internal | Backend only | Background task processing |

**Note:** The Celery Worker does NOT need external ingress. It communicates with the Backend via Redis and shares the same database connection.

---

## PREREQUISITES

### **Required Before Starting:**

**Azure Account Setup:**
- Active Azure subscription
- Owner or Contributor permissions on subscription
- Azure CLI installed (`az --version` to verify)

**GitHub Repository:**
- Repository: `johnmcd67/text_orders`
- Admin access to repository settings (to add secrets)
- Main branch protection (optional but recommended)

**Existing Resources:**
- IBM Cloud PostgreSQL database (current setup)
- Microsoft Graph API credentials (existing, will work from Azure)
- Anthropic API key (existing)

**Local Development Environment:**
- Docker Desktop installed and running
- Git repository cloned locally
- All Phase 4 changes committed (Docker files ready)

### **Azure Service Principal Creation (IT GUY TASK):**

**Note:** If service principal already exists from PDF Orders setup, you can reuse it or create a new one specifically for text orders.

**PowerShell Commands:**

```powershell
# Login to Azure
az login

# Get subscription ID
az account show --query id -o tsv
```

**If service principal does NOT exist yet, create it:**

```powershell
# Create service principal for text orders
az ad sp create-for-rbac --name "text-order-processing-github-actions" `
  --role contributor `
  --scopes /subscriptions/<your-subscription-id> `
  --sdk-auth
```

From the JSON output, provide:
- **AZURE_CLIENT_ID** = `clientId` from output
- **AZURE_CLIENT_SECRET** = `clientSecret` from output
- **AZURE_SUBSCRIPTION_ID** = `subscriptionId` from output
- **AZURE_TENANT_ID** = `tenantId` from output

---

## IMPLEMENTATION STEPS

### **PART 1: AZURE INFRASTRUCTURE PROVISIONING**

#### **Step 1.1: Create Resource Group**

```powershell
# Set variables
$RESOURCE_GROUP = "order-processing-text-rg"
$LOCATION = "uksouth"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Expected Output:**
```json
{
  "id": "/subscriptions/.../resourceGroups/order-processing-text-rg",
  "location": "uksouth",
  "name": "order-processing-text-rg",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

---

#### **Step 1.2: Create Azure Container Registry**

```powershell
$REGISTRY_NAME = "orderprocessingtextregistry"  # Must be globally unique, lowercase only

# Create container registry (Basic tier)
az acr create `
  --resource-group $RESOURCE_GROUP `
  --name $REGISTRY_NAME `
  --sku Basic `
  --admin-enabled true

# Get login server (save this)
az acr show --name $REGISTRY_NAME --query loginServer -o tsv
# Output: orderprocessingtextregistry.azurecr.io

# Get admin credentials (for GitHub Actions)
az acr credential show --name $REGISTRY_NAME
```

**Save the admin username and password** - these will be used in GitHub Actions.

---

#### **Step 1.3: Create Azure Redis Cache (Standard Tier)**

```powershell
$REDIS_NAME = "order-processing-text-redis"  # Must be globally unique

# Create Redis Cache (Standard tier, C1 size = 1GB cache)
az redis create `
  --resource-group $RESOURCE_GROUP `
  --name $REDIS_NAME `
  --location $LOCATION `
  --sku Standard `
  --vm-size C1 `
  --enable-non-ssl-port false

# This takes 15-20 minutes to provision - get a coffee!
```

**Monitor provisioning status:**
```powershell
az redis show --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query provisioningState -o tsv
```

**Once complete, get connection details:**
```powershell
# Get hostname
az redis show --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query hostName -o tsv
# Output: order-processing-text-redis.redis.cache.windows.net

# Get SSL port (should be 6380)
az redis show --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query sslPort -o tsv

# Get primary key (save this securely!)
az redis list-keys --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query primaryKey -o tsv
```

**Construct Redis URL for GitHub Secrets:**
```
rediss://:<primary-key>@order-processing-text-redis.redis.cache.windows.net:6380/0
```

**Important:** Use `rediss://` (with double 's') for SSL connection. The format is:
```
rediss://:<password>@<hostname>:<port>/<database>
```

---

#### **Step 1.4: Create Azure Blob Storage**

```powershell
$STORAGE_ACCOUNT = "orderprocessingtextstorage"  # Must be globally unique, lowercase, no hyphens

# Create storage account (Standard tier, LRS redundancy)
az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku Standard_LRS `
  --kind StorageV2

# Create blob container for temporary files
az storage container create `
  --name "text-order-processing-temp" `
  --account-name $STORAGE_ACCOUNT `
  --public-access off

# Get connection string (save this securely!)
az storage account show-connection-string `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --output tsv
```

**Connection string format:**
```
DefaultEndpointsProtocol=https;AccountName=orderprocessingtextstorage;AccountKey=<key>;EndpointSuffix=core.windows.net
```

---

#### **Step 1.5: Create Container Apps Environment**

```powershell
$ENVIRONMENT_NAME = "order-processing-text-env"

# Create Container Apps environment
az containerapp env create `
  --name $ENVIRONMENT_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION
```

**This takes 5-10 minutes.** The environment provides:
- Shared networking for all containers
- Log Analytics workspace (automatic)
- Auto-scaling infrastructure

---

### **PART 2: GITHUB REPOSITORY SECRETS SETUP**

Navigate to your GitHub repository: `https://github.com/johnmcd67/text_orders`

**Settings > Secrets and variables > Actions > New repository secret**

Add the following **18 secrets**:

| Secret Name | Value Source |
|-------------|--------------|
| `AZURE_CLIENT_ID` | Azure App Registration -> Application (client) ID |
| `AZURE_CLIENT_SECRET` | Azure App Registration -> Certificates & secrets |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscriptions -> Subscription ID |
| `AZURE_TENANT_ID` | Azure App Registration -> Directory (tenant) ID |
| `ACR_LOGIN_SERVER` | Step 1.2 output (Container Registry login server) |
| `ACR_USERNAME` | Step 1.2 output (Container Registry admin username) |
| `ACR_PASSWORD` | Step 1.2 output (Container Registry admin password) |
| `AZURE_REDIS_URL` | Step 1.3 output (Redis connection string) |
| `AZURE_STORAGE_CONNECTION_STRING` | Step 1.4 output (Blob Storage connection string) |
| `DATABASE_URL` | Existing IBM Cloud PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Existing Anthropic API key |
| `MICROSOFT_TENANT_ID` | Existing Microsoft Graph credential (from .env) |
| `MICROSOFT_CLIENT_ID` | Existing Microsoft Graph credential (from .env) |
| `MICROSOFT_CLIENT_SECRET` | Existing Microsoft Graph credential (from .env) |
| `MICROSOFT_OBJECT_ID` | Existing Microsoft Graph credential (from .env) |
| `JWT_SECRET` | Existing JWT signing key (from .env) |
| `VITE_AZURE_CLIENT_ID` | Same as AZURE_CLIENT_ID (for frontend) |
| `VITE_AZURE_TENANT_ID` | Same as AZURE_TENANT_ID (for frontend) |

**Note:** `FRONTEND_URL` and `VITE_API_URL` will be added in Part 7 after deployment (URLs not known until containers are deployed).

**Verification:** After adding all secrets, you should see 18 secrets listed under "Repository secrets".

---

### **PART 3: CODE MODIFICATIONS**

#### **Step 3.1: Update Blob Storage Container Name**

**File:** `backend/utils/blob_storage.py`

Update the container name constant:

```python
# Change from:
CONTAINER_NAME = "order-processing-temp"

# Change to:
CONTAINER_NAME = "text-order-processing-temp"
```

**Note:** The blob_storage.py helper already exists and is integrated with all tasks. Only the container name needs updating.

---

#### **Step 3.2: Add Health Checks to docker-compose.yml**

**File:** `docker-compose.yml`

Add health check configurations to ensure proper startup order and monitoring:

```yaml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
    depends_on:
      redis:
        condition: service_healthy

  worker:
    healthcheck:
      test: ["CMD", "celery", "-A", "backend.celery_app", "inspect", "ping", "-d", "celery@$$HOSTNAME"]
      interval: 60s
      timeout: 10s
      start_period: 30s
      retries: 3
    depends_on:
      redis:
        condition: service_healthy
```

---

#### **Step 3.3: Enhance Backend Health Endpoint**

**File:** `backend/main.py`

Update the `/api/health` endpoint to check all dependencies:

```python
@app.get("/api/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    status = {"status": "healthy"}

    # Check database connection
    try:
        db = get_db_helper()
        db.execute_query("SELECT 1")
        status["database"] = "connected"
    except Exception:
        status["database"] = "disconnected"
        status["status"] = "degraded"

    # Check Redis/Celery connection
    try:
        from backend.celery_app import celery_app
        result = celery_app.control.ping(timeout=1)
        status["redis"] = "connected" if result else "no_workers"
    except Exception:
        status["redis"] = "disconnected"
        status["status"] = "degraded"

    # Check Blob Storage (if configured)
    azure_storage = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if azure_storage:
        try:
            from backend.utils.blob_storage import ensure_temp_dir
            ensure_temp_dir()
            status["blob_storage"] = "connected"
        except Exception:
            status["blob_storage"] = "disconnected"

    return status
```

---

### **PART 4: DOCKERFILE REFINEMENTS**

#### **Step 4.1: Create Celery Worker Dockerfile**

**File:** `Dockerfile.worker`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Create temp directory (for local development compatibility)
RUN mkdir -p temp

# Health check for Celery (checks if worker is responsive)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD celery -A backend.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["celery", "-A", "backend.celery_app", "worker", "--loglevel=info", "--pool=solo"]
```

---

#### **Step 4.2: Verify Backend Dockerfile**

**File:** `backend/Dockerfile`

Ensure the existing Dockerfile includes a health check:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ../requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./backend/
COPY ../scripts/ ./scripts/

# Create temp directory
RUN mkdir -p temp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **PART 5: GITHUB ACTIONS CI/CD WORKFLOW**

**File:** `.github/workflows/deploy-azure.yml`

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  RESOURCE_GROUP: order-processing-text-rg
  REGISTRY_NAME: orderprocessingtextregistry
  REGISTRY_LOGIN_SERVER: orderprocessingtextregistry.azurecr.io
  FRONTEND_APP_NAME: order-processing-text-frontend
  BACKEND_APP_NAME: order-processing-text-backend
  WORKER_APP_NAME: order-processing-text-worker
  ENVIRONMENT_NAME: order-processing-text-env

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: |
            {
              "clientId": "${{ secrets.AZURE_CLIENT_ID }}",
              "clientSecret": "${{ secrets.AZURE_CLIENT_SECRET }}",
              "subscriptionId": "${{ secrets.AZURE_SUBSCRIPTION_ID }}",
              "tenantId": "${{ secrets.AZURE_TENANT_ID }}"
            }

      - name: Login to Azure Container Registry
        run: |
          az acr login --name ${{ env.REGISTRY_NAME }}

      - name: Build and Push Frontend Image
        run: |
          cd frontend
          docker build -t ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:${{ github.sha }} \
                       -t ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:latest .
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:${{ github.sha }}
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:latest

      - name: Build and Push Backend Image
        run: |
          docker build -t ${{ env.REGISTRY_LOGIN_SERVER }}/backend:${{ github.sha }} \
                       -t ${{ env.REGISTRY_LOGIN_SERVER }}/backend:latest \
                       -f backend/Dockerfile .
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/backend:${{ github.sha }}
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/backend:latest

      - name: Build and Push Celery Worker Image
        run: |
          docker build -t ${{ env.REGISTRY_LOGIN_SERVER }}/worker:${{ github.sha }} \
                       -t ${{ env.REGISTRY_LOGIN_SERVER }}/worker:latest \
                       -f Dockerfile.worker .
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/worker:${{ github.sha }}
          docker push ${{ env.REGISTRY_LOGIN_SERVER }}/worker:latest

      - name: Deploy Frontend Container App
        run: |
          az containerapp create \
            --name ${{ env.FRONTEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --environment ${{ env.ENVIRONMENT_NAME }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:${{ github.sha }} \
            --target-port 80 \
            --ingress external \
            --cpu 0.25 --memory 0.5Gi \
            --min-replicas 1 --max-replicas 3 \
            --registry-server ${{ env.REGISTRY_LOGIN_SERVER }} || \
          az containerapp update \
            --name ${{ env.FRONTEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/frontend:${{ github.sha }}

      - name: Deploy Backend Container App
        run: |
          az containerapp create \
            --name ${{ env.BACKEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --environment ${{ env.ENVIRONMENT_NAME }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/backend:${{ github.sha }} \
            --target-port 8000 \
            --ingress external \
            --cpu 0.5 --memory 1.0Gi \
            --min-replicas 1 --max-replicas 5 \
            --registry-server ${{ env.REGISTRY_LOGIN_SERVER }} \
            --secrets \
              database-url="${{ secrets.DATABASE_URL }}" \
              anthropic-api-key="${{ secrets.ANTHROPIC_API_KEY }}" \
              microsoft-tenant-id="${{ secrets.MICROSOFT_TENANT_ID }}" \
              microsoft-client-id="${{ secrets.MICROSOFT_CLIENT_ID }}" \
              microsoft-client-secret="${{ secrets.MICROSOFT_CLIENT_SECRET }}" \
              microsoft-object-id="${{ secrets.MICROSOFT_OBJECT_ID }}" \
              redis-url="${{ secrets.AZURE_REDIS_URL }}" \
              storage-connection-string="${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}" \
              jwt-secret="${{ secrets.JWT_SECRET }}" \
            --env-vars \
              DATABASE_URL=secretref:database-url \
              ANTHROPIC_API_KEY=secretref:anthropic-api-key \
              MICROSOFT_TENANT_ID=secretref:microsoft-tenant-id \
              MICROSOFT_CLIENT_ID=secretref:microsoft-client-id \
              MICROSOFT_CLIENT_SECRET=secretref:microsoft-client-secret \
              MICROSOFT_OBJECT_ID=secretref:microsoft-object-id \
              REDIS_URL=secretref:redis-url \
              AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string \
              JWT_SECRET=secretref:jwt-secret || \
          az containerapp update \
            --name ${{ env.BACKEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/backend:${{ github.sha }} \
            --set-env-vars \
              DATABASE_URL=secretref:database-url \
              ANTHROPIC_API_KEY=secretref:anthropic-api-key \
              MICROSOFT_TENANT_ID=secretref:microsoft-tenant-id \
              MICROSOFT_CLIENT_ID=secretref:microsoft-client-id \
              MICROSOFT_CLIENT_SECRET=secretref:microsoft-client-secret \
              MICROSOFT_OBJECT_ID=secretref:microsoft-object-id \
              REDIS_URL=secretref:redis-url \
              AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string \
              JWT_SECRET=secretref:jwt-secret

      - name: Deploy Celery Worker Container App
        run: |
          az containerapp create \
            --name ${{ env.WORKER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --environment ${{ env.ENVIRONMENT_NAME }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/worker:${{ github.sha }} \
            --ingress internal \
            --target-port 8000 \
            --cpu 0.5 --memory 1.0Gi \
            --min-replicas 1 --max-replicas 3 \
            --registry-server ${{ env.REGISTRY_LOGIN_SERVER }} \
            --secrets \
              database-url="${{ secrets.DATABASE_URL }}" \
              anthropic-api-key="${{ secrets.ANTHROPIC_API_KEY }}" \
              microsoft-tenant-id="${{ secrets.MICROSOFT_TENANT_ID }}" \
              microsoft-client-id="${{ secrets.MICROSOFT_CLIENT_ID }}" \
              microsoft-client-secret="${{ secrets.MICROSOFT_CLIENT_SECRET }}" \
              microsoft-object-id="${{ secrets.MICROSOFT_OBJECT_ID }}" \
              redis-url="${{ secrets.AZURE_REDIS_URL }}" \
              storage-connection-string="${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}" \
              jwt-secret="${{ secrets.JWT_SECRET }}" \
            --env-vars \
              DATABASE_URL=secretref:database-url \
              ANTHROPIC_API_KEY=secretref:anthropic-api-key \
              MICROSOFT_TENANT_ID=secretref:microsoft-tenant-id \
              MICROSOFT_CLIENT_ID=secretref:microsoft-client-id \
              MICROSOFT_CLIENT_SECRET=secretref:microsoft-client-secret \
              MICROSOFT_OBJECT_ID=secretref:microsoft-object-id \
              REDIS_URL=secretref:redis-url \
              AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string \
              JWT_SECRET=secretref:jwt-secret || \
          az containerapp update \
            --name ${{ env.WORKER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.REGISTRY_LOGIN_SERVER }}/worker:${{ github.sha }} \
            --set-env-vars \
              DATABASE_URL=secretref:database-url \
              ANTHROPIC_API_KEY=secretref:anthropic-api-key \
              MICROSOFT_TENANT_ID=secretref:microsoft-tenant-id \
              MICROSOFT_CLIENT_ID=secretref:microsoft-client-id \
              MICROSOFT_CLIENT_SECRET=secretref:microsoft-client-secret \
              MICROSOFT_OBJECT_ID=secretref:microsoft-object-id \
              REDIS_URL=secretref:redis-url \
              AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string \
              JWT_SECRET=secretref:jwt-secret

      - name: Health Check - Backend
        run: |
          BACKEND_URL=$(az containerapp show \
            --name ${{ env.BACKEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv)

          echo "Backend URL: https://$BACKEND_URL"

          # Wait 30 seconds for deployment to stabilize
          sleep 30

          # Health check with retries
          for i in {1..5}; do
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$BACKEND_URL/api/health)
            if [ "$HTTP_CODE" == "200" ]; then
              echo "Backend health check passed"
              exit 0
            fi
            echo "Attempt $i: Health check returned $HTTP_CODE, retrying in 10s..."
            sleep 10
          done

          echo "Backend health check failed after 5 attempts"
          exit 1

      - name: Health Check - Frontend
        run: |
          FRONTEND_URL=$(az containerapp show \
            --name ${{ env.FRONTEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv)

          echo "Frontend URL: https://$FRONTEND_URL"

          HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$FRONTEND_URL/health)
          if [ "$HTTP_CODE" == "200" ]; then
            echo "Frontend health check passed"
          else
            echo "Frontend health check failed with code $HTTP_CODE"
            exit 1
          fi

      - name: Display Application URLs
        run: |
          echo "Deployment Complete!"
          echo ""
          echo "Frontend URL:"
          az containerapp show \
            --name ${{ env.FRONTEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv
          echo ""
          echo "Backend URL:"
          az containerapp show \
            --name ${{ env.BACKEND_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv
```

---

### **PART 6: LOCAL DOCKER TESTING (Before Azure Deployment)**

Before deploying to Azure, test the Docker containers locally to catch issues early.

#### **Step 6.1: Create .env.example**

**File:** `.env.example`

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-...

# Microsoft Graph API (for email fetching)
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_OBJECT_ID=your-object-id

# Azure Storage (leave empty for local development, fill for Azure)
AZURE_STORAGE_CONNECTION_STRING=

# Redis (local development)
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET=your-secret-key-here
```

#### **Step 6.2: Test Docker Build and Run**

```bash
# Copy .env.example to .env and fill in real values
cp .env.example .env
# Edit .env with your actual credentials

# Build all containers
docker-compose build

# Expected output: Successfully built frontend, api, worker

# Start all services
docker-compose up -d

# Check container status
docker-compose ps
# All containers should show "running" status

# Check logs for errors
docker-compose logs api
docker-compose logs worker
docker-compose logs frontend

# Test backend health endpoint
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","database":"connected","redis":"connected"}

# Test frontend
curl http://localhost:80/health
# Expected: healthy

# Open browser to test UI
# http://localhost:80

# Stop all services when done testing
docker-compose down
```

**Success Criteria for Local Testing:**
- All 4 containers build without errors
- Backend health check returns 200
- Frontend loads in browser
- Can create a job and see progress updates
- Celery worker processes tasks successfully

---

### **PART 7: AZURE PRODUCTION DEPLOYMENT**

#### **Step 7.1: Commit and Push Changes**

```bash
# Ensure all new files are tracked
git add .

# Commit with descriptive message
git commit -m "Phase 5: Add Azure deployment configuration

- Add GitHub Actions workflow for CI/CD
- Add Dockerfile.worker for Celery
- Update blob storage container name for text orders
- Add health checks to docker-compose
- Configure container resource limits"

# Push to main branch (triggers automatic deployment)
git push origin main
```

#### **Step 7.2: Monitor GitHub Actions Deployment**

1. Go to GitHub repository: `https://github.com/johnmcd67/text_orders`
2. Click **Actions** tab
3. Select the latest workflow run (triggered by your push)
4. Monitor each step:
   - Checkout code
   - Azure Login
   - Build Frontend Image (3-5 minutes)
   - Build Backend Image (3-5 minutes)
   - Build Worker Image (3-5 minutes)
   - Deploy Frontend Container App (2-3 minutes)
   - Deploy Backend Container App (2-3 minutes)
   - Deploy Worker Container App (2-3 minutes)
   - Health Check - Backend
   - Health Check - Frontend
   - Display Application URLs

**Total deployment time: ~15-20 minutes**

#### **Step 7.3: Verify Deployment in Azure Portal**

1. Login to Azure Portal: `https://portal.azure.com`
2. Navigate to **Resource Groups** -> `order-processing-text-rg`
3. Verify all resources exist:
   - Container Apps Environment: `order-processing-text-env`
   - Container Registry: `orderprocessingtextregistry`
   - Redis Cache: `order-processing-text-redis`
   - Storage Account: `orderprocessingtextstorage`
   - Container App: `order-processing-text-frontend`
   - Container App: `order-processing-text-backend`
   - Container App: `order-processing-text-worker`

4. Check Container Apps:
   - Click **order-processing-text-backend**
   - Navigate to **Application Url** (copy this URL)
   - Should see: `https://order-processing-text-backend.<environment>.uksouth.azurecontainerapps.io`

5. Check Container Logs:
   - In Backend Container App -> **Log stream**
   - Look for startup messages: "Application startup complete"
   - No ERROR level logs should be visible

---

## MONITORING AND OBSERVABILITY

### **Azure Portal Monitoring**

#### **Container App Metrics:**
1. Navigate to Container App -> **Metrics**
2. Key metrics to monitor:
   - **CPU Usage:** Should stay below 70% on average
   - **Memory Usage:** Should stay below 80% on average
   - **Requests:** Track request volume
   - **Response Time:** Should be < 2 seconds for /api/health

#### **Log Analytics:**
1. Navigate to Container Apps Environment -> **Logs**
2. Use KQL queries to search logs:

```kusto
// All logs in last hour
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| order by TimeGenerated desc

// Error logs only
ContainerAppConsoleLogs_CL
| where Log_s contains "ERROR"
| order by TimeGenerated desc

// Specific container app
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "order-processing-text-backend"
| order by TimeGenerated desc
```

---

## TROUBLESHOOTING GUIDE

### **Issue 1: GitHub Actions Build Fails**

**Symptoms:**
- Docker build step fails with error messages
- "Error building image" in Actions log

**Debugging Steps:**
1. Check Dockerfile syntax errors
2. Verify all COPY paths exist
3. Test build locally: `docker build -t test-image -f Dockerfile .`
4. Check base image availability (Python 3.11, Node 20)

**Common Fixes:**
- Update requirements.txt if dependencies changed
- Ensure `.dockerignore` doesn't exclude necessary files
- Check file paths are correct (case-sensitive)

---

### **Issue 2: Container Registry Authentication Failed**

**Symptoms:**
- "failed to authorize" error during image push
- Azure login step fails

**Debugging Steps:**
1. Verify service principal credentials in GitHub Secrets
2. Check service principal has `Contributor` role on subscription
3. Verify registry exists: `az acr show --name orderprocessingtextregistry`

**Fix:**
```powershell
# Recreate service principal if needed
az ad sp create-for-rbac --name "text-order-processing-github-actions-new" `
  --role contributor `
  --scopes /subscriptions/<subscription-id> `
  --sdk-auth

# Update GitHub Secrets with new credentials
```

---

### **Issue 3: Container Fails to Start in Azure**

**Symptoms:**
- Container App shows "Provisioning" or "Failed" status
- Health checks fail

**Debugging Steps:**
1. Check container logs in Azure Portal: Container App -> **Log stream**
2. Look for startup errors (database connection, missing env vars)
3. Verify all secrets are set correctly
4. Check container resource limits (may need more memory)

**Common Issues:**
- **Database connection failed:** Verify `DATABASE_URL` secret is correct
- **Redis connection failed:** Check `AZURE_REDIS_URL` format (must use `rediss://`)
- **Import errors:** Dependency missing in requirements.txt
- **Port mismatch:** Ensure target-port matches EXPOSE in Dockerfile

**Fix:**
```powershell
# View detailed logs
az containerapp logs show `
  --name order-processing-text-backend `
  --resource-group order-processing-text-rg `
  --tail 100

# Restart container
az containerapp revision restart `
  --name order-processing-text-backend `
  --resource-group order-processing-text-rg
```

---

### **Issue 4: Redis Connection Timeout**

**Symptoms:**
- "Connection refused" errors in Celery worker logs
- Tasks not being picked up

**Debugging Steps:**
1. Verify Redis is provisioned: `az redis show --name order-processing-text-redis --resource-group order-processing-text-rg`
2. Check Redis is running: Status should be "Running"
3. Verify `AZURE_REDIS_URL` format

**Correct Redis URL format:**
```
rediss://:<primary-key>@order-processing-text-redis.redis.cache.windows.net:6380/0
```

**Common mistakes:**
- `redis://` (should be `rediss://` with SSL)
- Port 6379 (should be 6380 for SSL)
- Missing colon before password
- Wrong database number

**Fix:**
```powershell
# Get correct Redis connection string
$REDIS_HOST = az redis show --name order-processing-text-redis --resource-group order-processing-text-rg --query hostName -o tsv
$REDIS_KEY = az redis list-keys --name order-processing-text-redis --resource-group order-processing-text-rg --query primaryKey -o tsv

echo "rediss://:$REDIS_KEY@${REDIS_HOST}:6380/0"

# Update GitHub Secret with correct URL
```

---

### **Issue 5: Blob Storage Access Denied**

**Symptoms:**
- "BlobNotFound" or "AuthorizationFailure" errors
- Files not being saved

**Debugging Steps:**
1. Verify storage account exists
2. Check container "text-order-processing-temp" exists
3. Verify connection string is correct
4. Test connection locally with Azure Storage Explorer

**Fix:**
```powershell
# Recreate blob container
az storage container create `
  --name text-order-processing-temp `
  --account-name orderprocessingtextstorage `
  --public-access off

# Get fresh connection string
az storage account show-connection-string `
  --name orderprocessingtextstorage `
  --resource-group order-processing-text-rg `
  --output tsv

# Update GitHub Secret
```

---

### **Issue 6: Frontend Can't Connect to Backend**

**Symptoms:**
- Frontend loads but API calls fail with CORS errors
- Network errors in browser console

**Debugging Steps:**
1. Verify backend URL in frontend environment
2. Check CORS configuration in FastAPI backend
3. Ensure backend ingress is set to "external"

**Fix in backend/main.py:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## ROLLBACK PROCEDURES

### **Automatic Rollback**

The GitHub Actions workflow includes automatic rollback on health check failure:
- If health checks fail, the previous container revision remains active
- Failed deployment does NOT affect production traffic

### **Manual Rollback via Azure Portal**

1. Navigate to Container App (e.g., `order-processing-text-backend`)
2. Click **Revisions**
3. See list of previous revisions with timestamps
4. Find last working revision
5. Click **Activate** on that revision
6. Repeat for frontend and worker if needed

### **Manual Rollback via Azure CLI**

```powershell
# List all revisions for backend
az containerapp revision list `
  --name order-processing-text-backend `
  --resource-group order-processing-text-rg `
  --output table

# Activate previous revision
az containerapp revision activate `
  --revision order-processing-text-backend--<revision-suffix> `
  --resource-group order-processing-text-rg

# Deactivate failed revision
az containerapp revision deactivate `
  --revision order-processing-text-backend--<failed-revision> `
  --resource-group order-processing-text-rg
```

---

## SUCCESS CRITERIA CHECKLIST

### **Infrastructure Provisioning:**
- [ ] Resource group created: `order-processing-text-rg`
- [ ] Container registry created and accessible
- [ ] Azure Redis Cache provisioned (Standard tier)
- [ ] Azure Blob Storage created with container `text-order-processing-temp`
- [ ] Container Apps Environment created
- [ ] All resources in UK South region

### **GitHub Configuration:**
- [ ] Service principal created with Contributor role
- [ ] All 13 repository secrets added
- [ ] GitHub Actions workflow file committed
- [ ] Main branch protection rules configured (optional)

### **Code Updates:**
- [ ] Blob storage container name updated to `text-order-processing-temp`
- [ ] Health checks added to docker-compose.yml
- [ ] Backend health endpoint enhanced
- [ ] Dockerfile.worker created
- [ ] .dockerignore files created
- [ ] .env.example created

### **Local Testing:**
- [ ] Docker Compose builds all containers successfully
- [ ] Backend health check passes: `http://localhost:8000/api/health`
- [ ] Frontend loads: `http://localhost:80`
- [ ] Can create job and see progress
- [ ] Celery worker processes tasks
- [ ] Files saved to temp directory (local mode)

### **Azure Deployment:**
- [ ] GitHub Actions workflow runs without errors
- [ ] All 3 container images pushed to registry
- [ ] Frontend container app deployed and running
- [ ] Backend container app deployed and running
- [ ] Celery worker container app deployed and running
- [ ] Backend health check passes (production URL)
- [ ] Frontend accessible (production URL)

### **Production Verification:**
- [ ] Can access frontend via Azure URL
- [ ] Can start new job from UI
- [ ] Progress updates work (polling)
- [ ] Data review table loads
- [ ] Can approve job
- [ ] Tasks complete successfully
- [ ] CSV downloads work
- [ ] Files saved to Azure Blob Storage (not local temp)
- [ ] Redis connection works (Celery tasks execute)
- [ ] Database operations work

---

## COST OPTIMIZATION TIPS

### **Reduce Costs:**

1. **Use Minimum Replicas:**
   - Set `min-replicas` to 0 for non-production (containers stop when idle)
   - Production: Keep at 1 for availability

2. **Right-Size Containers:**
   - Monitor actual CPU/memory usage
   - Reduce allocation if consistently under 50%
   - Frontend: 0.25 CPU may be overkill if traffic is low

3. **Redis Cost Reduction:**
   - Standard tier costs £50/month
   - If 99.9% SLA not critical, downgrade to Basic tier (£15/month)
   - Trade-off: No high availability, single node

4. **Blob Storage Lifecycle:**
   - Configure automatic deletion of old temp files
   - Set 7-day retention policy on blob container

### **Monitor Spending:**

```powershell
# Check current month costs
az consumption usage list `
  --billing-period-name 202512 `
  --resource-group order-processing-text-rg
```

**Set up budget alerts:**
1. Azure Portal -> **Cost Management + Billing**
2. **Budgets** -> **Add**
3. Set monthly budget (e.g., £120)
4. Configure alerts at 80%, 100%, 120% thresholds

---

## FILES CREATED/MODIFIED IN PHASE 5

| File Path | Type | Purpose |
|-----------|------|---------|
| `.github/workflows/deploy-azure.yml` | New | CI/CD pipeline for Azure deployment |
| `.env.example` | New | Environment variable template |
| `Dockerfile.worker` | New | Celery worker container image |
| `backend/.dockerignore` | New | Exclude files from backend build |
| `frontend/.dockerignore` | New | Exclude files from frontend build |
| `backend/utils/blob_storage.py` | Modified | Update container name |
| `docker-compose.yml` | Modified | Add health checks |
| `backend/main.py` | Modified | Enhance health endpoint |
| `Docs/PHASE_5_PLAN.md` | New | This deployment guide |

---

## NEXT STEPS (PHASE 6)

After successful Phase 5 deployment, Phase 6 will focus on:

1. **Load Testing:**
   - Test with 200+ orders simultaneously
   - Verify auto-scaling works correctly
   - Optimize container resource allocation

2. **Performance Optimization:**
   - Add caching layer for repeat queries
   - Optimize database queries
   - Implement connection pooling

3. **Enhanced Monitoring:**
   - Set up Application Insights dashboards
   - Configure alerts for failures
   - Create custom metrics

4. **User Acceptance Testing:**
   - End-to-end testing with real users
   - Gather feedback on UI/UX
   - Fix any discovered bugs

---

**Document Version:** 1.0
**Last Updated:** December 2025
**Owner:** IT Team + Development Team

---

## READY TO DEPLOY!

This plan provides everything needed for successful Azure deployment. Follow the steps sequentially, verify each stage, and refer to troubleshooting section if issues arise.

**Estimated Total Time:**
- Infrastructure provisioning: 30-45 minutes (Redis takes longest)
- GitHub setup: 15 minutes
- Code modifications: 1-2 hours
- Local testing: 1 hour
- Azure deployment: 20 minutes (automatic via GitHub Actions)
- Production verification: 30 minutes

**Total: 4-5 hours of active work spread across Week 5-6**
