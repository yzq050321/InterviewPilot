-- V2 Batch5: 保存结构化综合能力评估；旧评估记录保留，默认 NULL。
-- 仅在本地备份完成后执行一次，不要重复执行。
ALTER TABLE evaluations
    ADD COLUMN competency_assessment JSON NULL;
