
type InterviewFormProps = {
  position: string;
  difficulty: string;
  loading: boolean;
  interviewId: number | null;
  onPositionChange: (value: string) => void;
  onDifficultyChange: (value: string) => void;
  onStartInterview: () => void;
};

export default function InterviewForm({
  position,
  difficulty,
  loading,
  interviewId,
  onPositionChange,
  onDifficultyChange,
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

      <div className="form-group">
        <label>面试难度</label>
        <div className="difficulty-options">
          {["简单", "中等", "困难"].map((level) => (
            <button
              key={level}
              type="button"
              className={
                difficulty === level
                  ? "difficulty active"
                  : "difficulty"
              }
              onClick={() =>
                onDifficultyChange(level)
              }
              disabled={loading}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <button
        className="start-button"
        onClick={onStartInterview}
        disabled={loading}
      >
        {loading && interviewId === null
          ? "AI 正在生成面试题..."
          : interviewId !== null
            ? "✦ 创建新的模拟面试 →"
            : "✦ 开始 AI 模拟面试 →"}
      </button>

      <p className="card-footer">
        由 AI 智能生成专属面试题目
      </p>
    </section>
  );
}