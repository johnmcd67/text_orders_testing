# Service Management

Run these from: `c:\Users\AI_USER\Desktop\Scripts\OrderIntake_web_app\text_orders`

## Start Services

### Option 1: Using Cursor Tasks (Recommended - Opens terminals within Cursor)

1. **Start Redis** (if not running as Windows service):
   
   **Option A: Install Redis as Windows Service (Recommended - Auto-starts on boot)**
   ```powershell
   # Navigate to Redis installation directory (usually C:\Program Files\Redis)
   cd "C:\Program Files\Redis"
   
   # Install Redis as a Windows service
   redis-server --service-install
   
   # Start the Redis service
   redis-server --service-start
   
   # Verify it's running
   Get-Service redis
   ```
   
   **Option B: Start Redis Manually (Temporary - stops when you close terminal)**
   ```powershell
   # Navigate to Redis installation directory
   cd "C:\Program Files\Redis"
   
   # Start Redis server
   redis-server
   ```
   
   **Option C: Check if Redis is Already Running**
   ```powershell
   # Check if Redis process is running
   Get-Process redis-server -ErrorAction SilentlyContinue
   
   # Or check if Redis service is installed and running
   Get-Service redis -ErrorAction SilentlyContinue
   ```
   
   **Download Redis for Windows:**
   - Download from: https://github.com/tporadowski/redis/releases
   - Install the `.msi` file
   - Default installation path: `C:\Program Files\Redis`

2. **Start all services in Cursor**:
   - Press `Ctrl+Shift+P`
   - Type "Tasks: Run Task"
   - Select **"Start All Services"**
   - This will open 3 integrated terminal tabs in Cursor:
     - FastAPI Backend (port 8000)
     - Celery Worker
     - Frontend Dev Server (port 5173)

3. **Or start individual services**:
   - Press `Ctrl+Shift+P` → "Tasks: Run Task"
   - Select individual task:
     - **FastAPI Backend** - Starts backend API server
     - **Celery Worker** - Starts Celery task worker
     - **Frontend Dev Server** - Starts Vite dev server

4. **Open the app**: **http://localhost:5173**

### Option 2: Using PowerShell Script (Opens pop-up windows)

```powershell
.\terminal_checks\start_services.ps1
```
Then open: **http://localhost:5173**

## Stop Services

### Using Cursor:
- Close the terminal tabs for each service (or use the stop button in terminal panel)

### Using PowerShell:
```powershell
.\terminal_checks\stop_services.ps1
```

## Check Status
```powershell
.\terminal_checks\check_status.ps1
```

