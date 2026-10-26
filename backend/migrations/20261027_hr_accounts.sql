-- InterviewPilot V2.3: invite-only HR accounts + trial applications.
-- Run ONCE after a MySQL backup. Does not modify existing interviews/jobs rows.
CREATE TABLE hr_users (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'hr',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME NULL,
  UNIQUE KEY uq_hr_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE trial_requests (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  company VARCHAR(200) NULL,
  note TEXT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_trial_requests_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
