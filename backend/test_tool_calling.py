
from langchain_core.messages import HumanMessage, ToolMessage

from app.services.llm_service import llm
from app.services.agent_tools import search_knowledge_tool


# 1. 注册可用工具
tools = [search_knowledge_tool]

llm_with_tools = llm.bind_tools(tools)

# 2. 构造对话消息
messages = [
    HumanMessage(
        content=(
            "你是一名 Python 后端技术面试官。"
            "请先检索 FastAPI Depends 的相关知识，"
            "再根据检索结果生成一道适合实习生的面试题。"
            "只输出最终的问题，不要给出答案。"
        )
    )
]

# 3. 第一次调用 DeepSeek：让模型选择工具
response = llm_with_tools.invoke(messages)

print("模型请求的工具：", response.tool_calls)

# 必须保留这条 AI 消息，以便后续匹配工具结果
messages.append(response)

# 4. Python 真正执行工具
for tool_call in response.tool_calls:

    if tool_call["name"] != search_knowledge_tool.name:
        raise ValueError("模型请求了未知工具")

    # 调用 RAG，查询 Chroma 知识库
    result = search_knowledge_tool.invoke(tool_call["args"])

    print("\nRAG 检索结果：")
    print(result)

    # 5. 将工具结果加入对话
    messages.append(
        ToolMessage(
            content=result,
            tool_call_id=tool_call["id"]
        )
    )

# 6. 第二次调用 DeepSeek：利用检索内容生成面试题
if response.tool_calls:
    final_response = llm.invoke(messages)

    print("\nAI 生成的最终面试题：")
    print(final_response.content)
else:
    print("\n模型未请求工具，直接回答：")
    print(response.content)