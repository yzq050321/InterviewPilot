-- Batch 10B: run ONCE after local MySQL backup. MySQL 8.4/InnoDB.
-- One row per candidate answer to a particular assistant message.
-- All writes authorized by the existing candidate bearer token.
CREATE TABLE interview_answer_attempts (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  interview_id INT NOT NULL,
  question_id INT NOT NULL,
  request_id VARCHAR(36) NOT NULL,
  answer_hash VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL,
  started_at DATETIME NOT NULL,
  next_question_id INT NULL,
  next_question TEXT NULL,
  next_stage VARCHAR(32) NULL,
  UNIQUE KEY uq_answer_attempt_question (interview_id, question_id),
  UNIQUE KEY uq_answer_attempt_request_id (request_id),
  KEY ix_interview_answer_attempts_interview_id (interview_id),
  CONSTRAINT fk_attempt_interview FOREIGN KEY (interview_id)
    REFERENCES interviews(id) ON DELETE CASCADE,
  CONSTRAINT fk_attempt_question FOREIGN KEY (question_id)
    REFERENCES messages(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
