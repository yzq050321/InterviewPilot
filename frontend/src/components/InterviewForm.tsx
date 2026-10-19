
type InterviewFormProps = {
  candidateName: string;
  position: string;
  loading: boolean;
  interviewId: number | null;
  onCandidateNameChange: (value: string) => void;
  onPositionChange: (value: string) => void;
  onStartInterview: () => void;
};

export default function InterviewForm({
  candidateName,
  position,
  loading,
  interviewId,
  onCandidateNameChange,
  onPositionChange,
  onStartInterview,
}: InterviewFormProps) {
  return (
    <section className="interview-card">
      <div className="card-heading">
        <div className="card-icon">▣</div>
        <div>
          <h2>创建一场模拟面试</h2>
          <p>配置你的专属 AI 面试体验</p>
        </div>
      </div>


      <div className="form-group">
        <label htmlFor="candidateName">候选人姓名</label>
        <input
          id="candidateName"
          type="text"
          value={candidateName}
          onChange={(e) =>
            onCandidateNameChange(e.target.value)
          }
          placeholder="请输入你的姓名"
          maxLength={100}
          autoComplete="name"
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="position">目标岗位</label>
        <input
          id="position"
          value={position}
          onChange={(e) =>
            onPositionChange(e.target.value)
          }
          placeholder="例如：Java 后端开发工程师"
          disabled={loading}
        />
      </div>


      <button
        className="start-button"
        onClick={onStartInterview}
        disabled={loading}
      >
        {loading && interviewId === null
          ? "AI 正在生成面试题..."
          : interviewId !== null
            ? "✦ 开始面试  →"
            : "✦ 开始面试 →"}
      </button>

      <p className="card-footer">
        由 AI 智能生成专属面试题目
      </p>
    </section>
  );
}