
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# backend 根目录
BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

# Chroma 数据库所在目录
CHROMA_DIR = BASE_DIR / "chroma_db"


def search_knowledge(query: str) -> str:
    """根据问题检索相关的岗位知识。"""

    # 1. 创建与建库时相同的 Embedding 模型
    embeddings = OpenAIEmbeddings(
        model="qwen3.7-text-embedding-flash",
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=os.environ["DASHSCOPE_BASE_URL"],
        check_embedding_ctx_length=False,
    )

    # 2. 加载已经建立的 Chroma 知识库
    vector_store = Chroma(
        collection_name="interview_knowledge",
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    # 3. 检索最相关的两个知识片段
    documents = vector_store.similarity_search(
        query,
        k=2,
    )

    # 4. 将检索结果整理成文本
    return "\n\n".join(
        doc.page_content for doc in documents
    )