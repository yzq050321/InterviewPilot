from app.services.agent_service import generate_question_agent

question = generate_question_agent(
    position="Python后端开发",
    difficulty="中等"
)

print("Agent 生成的第一道题：")
print(question)