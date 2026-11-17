-- Run ONLY on authorized staging database before enabling POC05 Execute.
-- Run as database administrator, never from the Excel add-in.
CREATE TABLE IF NOT EXISTS public.poc_price_execution_log (
 id BIGSERIAL PRIMARY KEY,
 job_key VARCHAR(100) NOT NULL,
 row_id TEXT NOT NULL,
 input_digest CHAR(64) NOT NULL,
 status VARCHAR(30) NOT NULL,
 target_id BIGINT NULL,
 error_message TEXT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 finished_at TIMESTAMPTZ NULL,
 CONSTRAINT poc_price_execution_log_uq UNIQUE(job_key,row_id)
);
