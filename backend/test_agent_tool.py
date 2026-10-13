from app.services.agent_tools import search_knowledge_tool

print("工具名称：", search_knowledge_tool.name)
print("工具描述：", search_knowledge_tool.description)
print("工具参数：", search_knowledge_tool.args)