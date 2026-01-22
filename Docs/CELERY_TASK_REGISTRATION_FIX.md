# Celery Task Registration Issue - Root Cause Analysis

**Date:** 2025-11-28
**Status:** CRITICAL - Jobs not processing
**Symptom:** Jobs created but never execute, Celery worker running but not picking up tasks

---

## Root Cause

**Celery tasks are not being properly registered** because of an import issue in `backend/celery_app.py`.

### Current (Broken) Code

**File:** `backend/celery_app.py` - Line 32
```python
from backend.tasks import task_fetch_emails, task_extract_emails, task_extract_data, task_tidy_emails
```

**File:** `backend/tasks/__init__.py`
```python
# Tasks package

```

**Problem:** The import statement tries to import module names from the `backend.tasks` package, but `__init__.py` is empty and doesn't expose these modules. This causes the import to fail silently or not register the tasks with Celery.

---

## Evidence

1. **Worker responds to ping but reports no active tasks:**
   ```json
   {"celery@SERVER04": {"ok": "pong"}}
   ```

2. **Tasks ARE registered when imported correctly:**
   ```
   ['backend.tasks.task_fetch_emails.fetch_emails_task',
    'backend.tasks.task_extract_emails.extract_emails_task',
    'backend.tasks.task_extract_data.extract_data_task',
    'backend.tasks.task_tidy_emails.tidy_emails_task']
   ```

3. **Redis queue is empty (no tasks being queued):**
   ```
   LLEN "celery" → 0
   ```

4. **Job 221 created but never executed:**
   - Created: 13:32:34
   - Marked failed: 14:09:56 (37 minutes later)
   - NO log entries for this job
   - Worker never picked it up

---

## Comparison with Working Sister Project (pdf_orders)

**pdf_orders celery_app.py** - Line 32:
```python
from backend.tasks import task_ocr, task_fetch_emails, task_extract_data, task_tidy_emails
```

Note: `task_ocr` instead of `task_extract_emails`, but same import pattern.

**The difference:** The pdf_orders project may have a different __init__.py or relies on a different import mechanism.

---

## Solution Options

### Option 1: Fix tasks/__init__.py (Recommended)

Update `backend/tasks/__init__.py` to expose task modules:

```python
# Tasks package
from backend.tasks import task_fetch_emails
from backend.tasks import task_extract_emails
from backend.tasks import task_extract_data
from backend.tasks import task_tidy_emails

__all__ = [
    'task_fetch_emails',
    'task_extract_emails',
    'task_extract_data',
    'task_tidy_emails'
]
```

### Option 2: Change celery_app.py imports

Update `backend/celery_app.py` line 32 to import task functions directly:

```python
# Import tasks explicitly to register them with Celery
from backend.tasks.task_fetch_emails import fetch_emails_task
from backend.tasks.task_extract_emails import extract_emails_task
from backend.tasks.task_extract_data import extract_data_task
from backend.tasks.task_tidy_emails import tidy_emails_task
```

This ensures the task decorators execute and register with Celery.

---

## Testing the Fix

After implementing either solution:

1. **Restart Celery worker:**
   ```bash
   # Kill existing worker
   # Start new worker
   celery -A backend.celery_app worker --loglevel=info
   ```

2. **Verify tasks are registered:**
   ```bash
   celery -A backend.celery_app inspect registered
   ```

3. **Test job creation via API:**
   ```bash
   # Start job through frontend or curl with auth token
   # Check logs for task execution
   tail -f backend/logs/order_intake_$(date +%Y-%m-%d).log
   ```

4. **Verify Redis queue:**
   ```bash
   redis-cli -n 1 LLEN celery
   ```

---

## Additional Findings

### Health Check Misleading

**File:** `backend/main.py` - Line 604
```python
workers = inspect.active()  # Returns active TASKS, not workers
```

This incorrectly reports "no workers" when worker is idle. Should use:
```python
workers = inspect.ping()  # Returns workers that respond
```

### Worker Running on Correct Redis Database

- Worker connected to: `redis://localhost:6379/1` ✓
- FastAPI app using: `redis://localhost:6379/1` ✓
- Configuration matches `.env`: `REDIS_URL=redis://localhost:6379/1` ✓

No database mismatch issue.

---

## Recommended Action

**Implement Option 2** (change celery_app.py imports) because:
1. Clearer and more explicit
2. Follows pattern used in main.py (lines 29-32)
3. No ambiguity about what's being imported
4. Easier to debug if imports fail

**After fix:**
1. Stop Celery worker (Ctrl+C in Terminal 2)
2. Restart Celery worker with `celery -A backend.celery_app worker --loglevel=info`
3. Verify tasks register correctly
4. Test new job execution

---

## Files to Modify

- [ ] `backend/celery_app.py` - Line 32 (import statement)
- [ ] Restart Celery worker process
- [ ] Test job execution
- [ ] Optional: Fix health check in `backend/main.py` line 604

---

**Priority:** CRITICAL
**Estimated Fix Time:** 2 minutes
**Testing Time:** 5 minutes
