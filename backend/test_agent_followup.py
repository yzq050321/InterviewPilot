
from app.services.agent_service import generate_followup_agent


history = [
    {
        "role": "assistant",
        "content": "请解释 FastAPI 的 Depends 有什么作用？"
    },
    {
        "role": "user",
        "content": "Depends 用于依赖注入，可以获取数据库 Session。"
    }
]

question = generate_followup_agent(
    position="Python后端开发",
    difficulty="中等",
    history=history
)

print("Agent 生成的追问：")
print(question)