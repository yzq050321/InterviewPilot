
from langchain_core.tools import tool

from app.services.rag_service import search_knowledge


@tool
def search_knowledge_tool(query: str) -> str:
    """
    检索 Python 后端开发知识库。

    当需要查询 Python、FastAPI、MySQL、
    异步编程等技术知识时使用此工具。

    Args:
        query: 需要检索的技术问题或知识点
    """

    return search_knowledge(query)