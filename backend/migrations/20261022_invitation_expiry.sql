-- InterviewPilot Batch 10A: run ONCE after local MySQL backup.
-- Warning: MySQL DDL auto-commits. Check schema before running.
-- UTC timestamps; existing links receive 7 days from migration time.
ALTER TABLE job_postings
  ADD COLUMN invite_expires_at DATETIME NULL;

UPDATE job_postings
  SET invite_expires_at = UTC_TIMESTAMP() + INTERVAL 7 DAY
  WHERE invite_expires_at IS NULL;
