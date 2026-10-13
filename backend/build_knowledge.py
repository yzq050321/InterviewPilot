
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# 获取 backend 目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent

# 知识文件位置
KNOWLEDGE_FILE = BASE_DIR / "knowledge" / "python_backend.md"

# 向量数据库保存位置
CHROMA_DIR = BASE_DIR / "chroma_db"


load_dotenv(BASE_DIR / ".env")

def build_knowledge_base():

    # 1. 读取 Markdown 知识文件
    loader = TextLoader(
        str(KNOWLEDGE_FILE),
        encoding="utf-8"
    )
    documents = loader.load()

    print(f"读取文档数量：{len(documents)}")

    # 2. 把文档切分为较小的知识片段
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    print(f"切分后的 Chunk 数量：{len(chunks)}")

    # 3. 加载中文 Embedding 模型
    embeddings = OpenAIEmbeddings(
        model="qwen3.7-text-embedding-flash",
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=os.environ["DASHSCOPE_BASE_URL"],
        check_embedding_ctx_length=False,
    )
    # 4. 将 Chunk 转换为向量并保存到 Chroma
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="interview_knowledge"
    )

    print("知识库构建完成！")


if __name__ == "__main__":
    build_knowledge_base()