"""招聘邀请面试的固定维度覆盖与证据校验（无 AI/数据库依赖）。

候选人可以提前结束，因此未覆盖维度必须为空分而不是擅自推断。
每个维度 2 次回答：一个场景问题和一个针对回答的追问。
"""
from __future__ import annotations

from typing import Any

DIMENSIONS = ("technical", "communication", "learning", "execution")
LABELS = {
    "technical": "技术能力",
    "communication": "沟通能力（文字情境回答）",
    "learning": "学习能力（情境回答）",
    "execution": "执行能力（情境回答）",
}
QUESTION_LIMIT = 8
CLOSING_MESSAGE = "四类面试问题已完成。感谢你的回答，请点击「结束面试」提交本次面试。"


# 已回答的第 n 个问题后，下一道问题的类型；n=8 表示无须再调用 AI。
def stage_after_answer(answered_count: int) -> str:
    if answered_count < 1:
        raise ValueError("至少需要一条候选人回答")
    if answered_count >= QUESTION_LIMIT:
        return "finished"
    return {
        1: "technical_followup",
        2: "communication_intro",
        3: "communication_followup",
        4: "learning_intro",
        5: "learning_followup",
        6: "execution_intro",
        7: "execution_followup",
    }[answered_count]


def answers_by_dimension(history: list[dict[str, Any]]) -> dict[str, list[str]]:
    """根据实际候选人回答顺序分组，不依赖模型自行判定覆盖度。"""
    result: dict[str, list[str]] = {key: [] for key in DIMENSIONS}
    answer_index = 0
    for item in history:
        if item.get("role") != "user":
            continue
        content = item.get("content")
        if answer_index < QUESTION_LIMIT and isinstance(content, str):
            dimension = DIMENSIONS[answer_index // 2]
            result[dimension].append(content)
        answer_index += 1
    return result


def verify_competency_evidence(raw: Any, history: list[dict[str, Any]]) -> dict[str, Any]:
    """模型分数必须有从对应维度原回答中逐字摘取的证据，否则记为未评估。

    不提供任意文本作为可执行的指令；这是从 LLM JSON 中提取的一份受控报告。
    """
    data = raw if isinstance(raw, dict) else {}
    groups = answers_by_dimension(history)
    cleaned: dict[str, dict[str, Any]] = {}
    for key in DIMENSIONS:
        item = data.get(key)
        if not isinstance(item, dict):
            item = {}
        score = item.get("score")
        quote = item.get("evidence")
        observation = item.get("observation")
        limitations = item.get("limitations")
        valid_score = isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 100
        valid_quote = (
            isinstance(quote, str)
            and 4 <= len(quote.strip()) <= 250
            and any(quote.strip() in answer for answer in groups[key])
        )
        # 防止猜测或编造的证据展示为“已核实”。
        if not (valid_score and valid_quote):
            cleaned[key] = {
                "score": None,
                "evidence": None,
                "observation": "该维度缺少可核验的回答证据，暂无可靠评分。",
                "limitations": "需要 HR 人工复核，或通过后续面试补充确认。",
                "answer_count": len(groups[key]),
            }
        else:
            cleaned[key] = {
                "score": score,
                "evidence": quote.strip(),
                "observation": observation.strip()[:600] if isinstance(observation, str) and observation.strip() else "仅供面试参考。",
                "limitations": limitations.strip()[:400] if isinstance(limitations, str) and limitations.strip() else "仅依据本次文字面试，不能代表实际工作表现。",
                "answer_count": len(groups[key]),
            }
    return {
        "version": 1,
        "dimensions": cleaned,
        "review_notice": "AI 仅根据文字情境问答辅助整理表现；分数不是胜任力的客观测量，不可作为自动录用或淘汰决定。请 HR 结合其他材料人工复核。",
    }
