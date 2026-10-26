-- InterviewPilot V2.2: resume-grounded interview.
-- Run ONCE after a MySQL backup. Stores parsed resume text only; the original
-- PDF/DOCX is never written to disk or to the database.
ALTER TABLE interviews
  ADD COLUMN resume_text TEXT NULL,
  ADD COLUMN resume_filename VARCHAR(255) NULL,
  ADD COLUMN resume_consent_at DATETIME NULL;
