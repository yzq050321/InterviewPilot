import { useEffect, useState } from "react";
import { getPipelineDetail, saveFollowup, stageLabels } from "../services/pipelineApi";
import type { PipelineDetail, RecruitmentStage } from "../services/pipelineApi";
import "./Pipeline.css";

export default function PipelinePanel({ interviewId, demoMode }: { interviewId: number; demoMode: boolean }) {
  const [data, setData] = useState<PipelineDetail | null>(null);
  const [stage, setStage] = useState<RecruitmentStage>("new");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getPipelineDetail(interviewId).then((fresh) => {
      if (!cancelled) { setData(fresh); setStage(fresh.stage); setError(""); }
    }).catch((err: unknown) => { if (!cancelled) setError(err instanceof Error ? err.message : "跟进记录加载失败"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [interviewId]);

  async function submit() {
    if (saving || demoMode || !note.trim()) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const updated = await saveFollowup(interviewId, stage, note.trim());
      setData((old) => old ? { ...old, stage: updated.stage,
        history: [updated.followup, ...old.history] } : old);
      setNote(""); setNotice("招聘跟进已保存，历史记录不会被覆盖。");
    } catch (err) { setError(err instanceof Error ? err.message : "保存失败"); }
    finally { setSaving(false); }
  }

  return <section className="pipeline-panel" aria-labelledby="pipeline-heading">
    <h3 id="pipeline-heading">招聘流程与 HR 跟进</h3>
    <p>由 HR 人工更新，独立于 AI 评分和报告复核；不代表自动录用或淘汰。</p>
    {loading ? <p>加载招聘进度中…</p> : data && <>
      <p><strong>当前阶段：</strong><span className="pipeline-tag">{stageLabels[data.stage]}</span></p>
      {demoMode ? <p>演示账号只能查看以下虚构跟进历史，不能修改。</p> :
      <div className="pipeline-controls">
        <label>目标阶段<select aria-label="选择招聘阶段" value={stage} disabled={saving}
          onChange={(e) => setStage(e.target.value as RecruitmentStage)}>
          {Object.entries(stageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label className="pipeline-note">跟进备注（必填，最多 1000 字）
          <textarea aria-label="招聘跟进备注" rows={3} maxLength={1000} value={note}
            disabled={saving} placeholder="记录本次沟通计划或事实，不写不必要的敏感个人信息"
            onChange={(e) => setNote(e.target.value)}/>
        </label>
        <button type="button" disabled={saving || !note.trim()} onClick={() => { void submit(); }}>
          {saving ? "正在保存…" : "保存阶段 / 跟进"}
        </button>
      </div>}
      {notice && <p role="status">{notice}</p>}
      <h4>跟进历史（{data.history.length}）</h4>
      {data.history.length === 0 ? <p>暂无跟进记录。</p> : <ul className="pipeline-history">
        {data.history.map((item) => <li key={item.id}>
          <div><strong>{stageLabels[item.old_stage]} → {stageLabels[item.new_stage]}</strong></div>
          <div style={{ whiteSpace: "pre-wrap" }}>{item.note}</div>
          <time>{item.created_at.replace("T", " ").slice(0, 19)}</time>
        </li>)}
      </ul>}
    </>}
    {error && <p className="pipeline-error" role="alert">{error}</p>}
  </section>;
}
