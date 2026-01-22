-- Migration: Add failure summary columns to job_runs table
-- Run this against your PostgreSQL database to enable the Failed Orders Summary feature

ALTER TABLE public.job_runs
ADD COLUMN IF NOT EXISTS failure_context JSONB,
ADD COLUMN IF NOT EXISTS failure_summary TEXT,
ADD COLUMN IF NOT EXISTS failure_summary_generated_at TIMESTAMP WITHOUT TIME ZONE;

-- Add comment for documentation
COMMENT ON COLUMN public.job_runs.failure_context IS 'JSONB array storing detailed failure context from customer_id and sku_extraction subagents';
COMMENT ON COLUMN public.job_runs.failure_summary IS 'Cached AI-generated summary of order failures';
COMMENT ON COLUMN public.job_runs.failure_summary_generated_at IS 'Timestamp when failure_summary was generated';
