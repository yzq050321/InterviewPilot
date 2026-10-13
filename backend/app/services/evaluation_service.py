
import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_service import llm


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_score: Optional[int] = Field(
        ge=0, le=100
    )

    completeness_score: Optional[int] = Field(
        ge=0, le=100
    )

    clarity_score: Optional[int] = Field(
        ge=0, le=100
    )

    overall_score: Optional[int] = Field(
        ge=0, le=100
    )

    summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


def generate_evaluation(
    position: str,
    difficulty: str,
    history: list[dict]
) -> EvaluationReport:

    # 1. 检查是否有用户回答
    user_answers = [
        item for item in history
        if item["role"] == "user"
    ]

    if not user_answers:
        raise ValueError("没有用户回答，无法生成评估报告")

    # 2. 构建面试历史文本
    conversation = []

    for item in history:
        role = (
            "面试官"
            if item["role"] == "assistant"
            else "候选人"
        )

        conversation.append(
            f"{role}：{item['content']}"
        )

    history_text = "\n".join(conversation)

    # 3. 定义评估规则
    system_prompt = """
你是一名专业的软件开发技术面试评估官。

请根据候选人的真实回答进行客观评估。

评分维度：
1. technical_score：技术知识准确性
2. completeness_score：回答完整性
3. clarity_score：表达清晰度
4. overall_score：综合表现

评分范围为0到100。

重要规则：
- 只能根据提供的面试记录进行评价。
- 不要编造候选人没有说过的内容。
- 证据不足的维度使用null。
- strengths、weaknesses、suggestions必须是字符串数组。
- 评价要具体、建设性。
- 只返回一个合法JSON对象。
- 不要输出Markdown代码块。
- 不要输出JSON以外的解释。

JSON字段必须包含：
technical_score
completeness_score
clarity_score
overall_score
summary
strengths
weaknesses
suggestions
"""

    # 4. 构建请求
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"面试岗位：{position}\n"
                f"面试难度：{difficulty}\n\n"
                f"完整面试记录：\n{history_text}"
            )
        )
    ]

    # 5. 调用 DeepSeek
    response = llm.invoke(messages)

    # 6. 解析 JSON
    raw_result = response.content

    if not isinstance(raw_result, str):
        raise ValueError("AI返回内容不是字符串")

    result_dict = json.loads(raw_result)

    # 7. 使用 Pydantic 验证
    report = EvaluationReport.model_validate(
        result_dict
    )

    return report