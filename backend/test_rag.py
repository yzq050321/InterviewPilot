
from app.services.rag_service import search_knowledge


question = "FastAPI 的 Depends 有什么作用？"

result = search_knowledge(question)

print("用户问题：", question)
print("\n检索到的知识：")
print(result)