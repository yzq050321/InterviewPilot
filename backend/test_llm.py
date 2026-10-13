
# 导入 Python 标准库
import os

# 导入 dotenv，用于读取 .env 配置文件
from dotenv import load_dotenv

# 导入 LangChain 的聊天模型
from langchain_openai import ChatOpenAI

# 导入 LangChain 的 Prompt 模板
from langchain_core.prompts import ChatPromptTemplate

# 第一步：加载环境变量
load_dotenv()

# 第二步：读取 DeepSeek 配置
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL")
model_name = os.getenv("DEEPSEEK_MODEL")

# 检查 API Key 是否配置
if not api_key or api_key == "你的DeepSeek_API_Key":
    raise ValueError("请先在 .env 文件中配置 DeepSeek API Key")

# 第三步：创建大模型对象
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    timeout=30,
    max_retries=2
)

# 第四步：创建 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "你是一名专业的技术面试官，"
        "负责为求职者生成技术面试题。"
        "一次只生成一道问题，不要提供答案。"
    ),
    (
        "human",
        "请为{position}岗位生成一道{difficulty}难度的面试题。"
    )
])

# 第五步：创建 LangChain 调用链
chain = prompt | llm

# 第六步：调用大模型
try:
    response = chain.invoke({
        "position": "Java后端开发实习生",
        "difficulty": "中等"
    })

    # 输出 AI 生成的面试题
    print("AI 面试官：")
    print(response.content)

except Exception as e:
    print("调用 DeepSeek 失败：")
    print(str(e))