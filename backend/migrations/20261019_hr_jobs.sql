-- InterviewPilot V2 / 本地 MySQL 单次迁移
-- 执行前必须备份 interview_pilot 数据库。
-- 仅在 Windows 本地 MySQL 环境执行，不要在腾讯云上执行。
-- 二次运行会在添加 job_id 时失败：请勿重复执行。

CREATE TABLE IF NOT EXISTS job_postings (
  id INT NOT NULL AUTO_INCREMENT,
  title VARCHAR(100) NOT NULL,
  position VARCHAR(100) NOT NULL,
  requirements TEXT NOT NULL,
  difficulty VARCHAR(30) NOT NULL,
  invite_code VARCHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY ix_job_postings_invite_code (invite_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE interviews
  ADD COLUMN job_id INT NULL,
  ADD INDEX ix_interviews_job_id (job_id),
  ADD CONSTRAINT fk_interviews_job_id
    FOREIGN KEY (job_id) REFERENCES job_postings(id)
    ON DELETE SET NULL;
