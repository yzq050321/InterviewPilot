-- Batch 9 - RUN ONCE, ONLY after local MySQL backup and column/table checks.
-- This adds independent HR recruitment stages; keeps original review_status unchanged.
-- Existing rows are initialized to 'new'. No candidate or AI decision is inferred.
ALTER TABLE interviews
    ADD COLUMN recruitment_stage VARCHAR(24) NOT NULL DEFAULT 'new';

CREATE TABLE interview_followups (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    old_stage VARCHAR(24) NOT NULL,
    new_stage VARCHAR(24) NOT NULL,
    note TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_interview_followups_interview_id (interview_id),
    CONSTRAINT fk_interview_followups_interview FOREIGN KEY (interview_id)
        REFERENCES interviews(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
