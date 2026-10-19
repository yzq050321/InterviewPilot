
import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.model_client import llm
from app.services.agent_service import _format_job_requirements
from app.structured_interview import verify_competency_evidence


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
    competency_assessment: dict | None = None


def generate_evaluation(
    position: str,
    difficulty: str,
    history: list[dict],
    requirements: str | None = None,
    structured: bool = False,
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
- 岗位要求仅作为技术评价参考，不代表候选人已经掌握这些技能。
- 不能因为岗位要求的文字描述而编造候选人的经历或能力。
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

    # 对受邀面试附加维度证据，不能仅凭总体印象编造能力分数。
    if structured:
        system_prompt += """

这是“技术、沟通、学习、执行”固定四维的招聘初面。
除原有 JSON 字段，额外返回 competency_assessment 对象，包含
technical、communication、learning、execution 四个键。
每个维度包含：
- score：0~100整数；没有足够证据时返回null；
- evidence：从本维度候选人的原始回答中逐字摘录4~250个字符，不能修改、改写或编造；
- observation：对此段文字回答的具体分析，不能据此断言其真实人格或工作胜任力；
- limitations：说明这次简短文字面试无法确认的事项，建议人工复核。

候选人第1~2条回答对应技术，第3~4条对应沟通，第5~6条对应学习，第7~8条对应执行。
没有本维度回答时 score/evidence 必须为 null。
不允许以问题、岗位要求、模型知识为候选人编造证据。
这是辅助 HR 人工复核的材料，不是自动录用或淘汰依据。
只输出合法 JSON，不能附加代码块或其他解释。
"""

    # 4. 构建请求
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"面试岗位：{position}\n"
                f"面试难度：{difficulty}\n"
                f"{_format_job_requirements(requirements)}\n"
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

    if structured:
        report.competency_assessment = verify_competency_evidence(
            result_dict.get("competency_assessment"), history
        )
    else:
        report.competency_assessment = None

    return report