-- InterviewPilot V2 batch 6; BACK UP the LOCAL MySQL database first.
-- Run exactly once on the local interview_pilot schema.
-- NULL evaluation_state preserves compatibility with legacy rows.
ALTER TABLE interviews
    ADD COLUMN evaluation_state VARCHAR(20) NULL,
    ADD COLUMN evaluation_error VARCHAR(255) NULL,
    ADD COLUMN evaluation_started_at DATETIME NULL,
    ADD COLUMN review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ADD COLUMN review_note TEXT NULL,
    ADD COLUMN reviewed_at DATETIME NULL;
