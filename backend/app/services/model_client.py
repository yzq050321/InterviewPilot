
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# 找到 backend 目录
BASE_DIR = Path(__file__).resolve().parents[2]

# 加载 backend/.env
load_dotenv(BASE_DIR / ".env")


# 创建 DeepSeek 模型
llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com"
    ),
    temperature=0.7,
    timeout=30,
    max_retries=2
)