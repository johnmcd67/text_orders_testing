# Communication Log - Text Orders Web Application

## 2025-12-09 - Failed Orders Summary Feature Progress

### Feature Overview
Adding an on-demand AI-generated summary for failed orders, displayed on both DataReviewTable and ResultsDownload pages.

### COMPLETED Tasks:
1. SQL migration file created: `postgres_schema/migration_add_failure_summary.sql`
2. Modified `backend/utils/database.py` - Added `fuzzy_match_customer` 3-tuple return + 4 helper methods
3. Modified `backend/subagents/customer_id.py` - Captures failure_context
4. Modified `backend/subagents/sku_extraction.py` - Captures failure_context
5. Modified `backend/tasks/task_extract_data.py` - Collects and saves failure contexts
6. Created `backend/prompts/failure_summary.txt` - Prompt template
7. Added `FailureSummaryResponse` model to `backend/models.py`
8. Added `/api/jobs/{job_id}/failure-summary` endpoint to `backend/main.py`
9. Added `FailureSummaryResponse` type to `frontend/src/types/job.types.ts`
10. Added `getFailureSummary` method to `frontend/src/api/jobsApi.ts`
11. Created `frontend/src/components/FailureSummaryPanel.tsx`

### REMAINING Tasks:
1. Integrate FailureSummaryPanel into DataReviewTable.tsx
2. Integrate FailureSummaryPanel into ResultsDownload.tsx
3. Install react-markdown dependency: `cd frontend && npm install react-markdown`

### User Action Required:
- Run SQL migration against database (user will do manually)
- Install react-markdown: `cd frontend && npm install react-markdown`

