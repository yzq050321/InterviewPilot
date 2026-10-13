from app.services.agent_service import run_interview_agent


question = run_interview_agent(
    "你是一名 Python 后端技术面试官。"
    "请先查询知识库中的数据库事务知识，"
    "再生成一道适合实习生的数据库事务面试题。"
    "只输出问题，不提供答案。"
)

print("Agent 生成的面试题：")
print(question)