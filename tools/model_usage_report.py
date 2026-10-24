"""Offline per-interview cost and token usage summary; never calls model APIs.

Run from project root: python tools/model_usage_report.py
Optional: --interview-id 7; --path ...
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import json
import os
from pathlib import Path


def summarize(path: Path, interview_id: int | None = None):
    records = []
    invalid = 0
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                record = json.loads(line)
                if isinstance(record, dict) and record.get("kind") in ("llm_usage", "interview_link"):
                    records.append(record)
            except (ValueError, UnicodeDecodeError):
                invalid += 1

    linked = {r.get("trace_id"): r.get("interview_id") for r in records if r.get("kind") == "interview_link"}
    calls = []
    for record in records:
        if record.get("kind") != "llm_usage":
            continue
        r = dict(record)
        if r.get("interview_id") is None:
            r["interview_id"] = linked.get(r.get("trace_id"))
        if interview_id is None or r.get("interview_id") == interview_id:
            calls.append(r)

    stats = defaultdict(lambda: {"calls": 0, "errors": 0, "input_tokens": 0, "output_tokens": 0, "known_tokens": 0, "known_cost": 0, "estimated_cny": Decimal(0), "elapsed_ms": 0})
    for r in calls:
        key = (r.get("interview_id"), r.get("stage"))
        s = stats[key]
        s["calls"] += 1
        s["errors"] += r.get("status") != "ok"
        s["elapsed_ms"] += r.get("elapsed_ms") or 0
        if isinstance(r.get("input_tokens"), int) and isinstance(r.get("output_tokens"), int):
            s["known_tokens"] += 1
            s["input_tokens"] += r["input_tokens"]
            s["output_tokens"] += r["output_tokens"]
        if r.get("estimated_cny") is not None:
            try:
                s["estimated_cny"] += Decimal(str(r["estimated_cny"]))
                s["known_cost"] += 1
            except Exception:
                pass
    return stats, len(calls), invalid


def main():
    parser = argparse.ArgumentParser(description="InterviewPilot offline model usage report")
    parser.add_argument("--path", default=os.getenv("MODEL_USAGE_LOG_PATH", str(Path.home()/".interviewpilot"/"model_usage.jsonl")))
    parser.add_argument("--interview-id", type=int, default=None)
    args = parser.parse_args()
    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"尚无用量日志: {path}")
        print("先设置 MODEL_USAGE_ENABLED=1 并用虚构测试数据触发一场 AI 面试。")
        return
    stats, n, invalid = summarize(path, args.interview_id)
    print("=== InterviewPilot V2.1：DeepSeek ChatOpenAI 调用成本（仅估算）===")
    print(f"日志文件：{path}")
    print(f"模型调用数：{n}；无效日志行：{invalid}")
    print("注：未包括 Embedding、云服务器、电力等费用；失败请求可能消耗未知 Token。")
    for (iid, stage), s in sorted(stats.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        who = str(iid) if iid is not None else "未关联/创建失败"
        money = (f"¥{s['estimated_cny']:.6f} (已计价 {s['known_cost']}/{s['calls']} 次)"
                 if s["known_cost"] else "未设置有效单价/未提供用量")
        print(f"面试 #{who} | {stage}: 调用 {s['calls']} 次，失败 {s['errors']} 次，"
              f"输入 {s['input_tokens']}，输出 {s['output_tokens']} Token"
              f"（已知用量 {s['known_tokens']}/{s['calls']} 次），"
              f"耗时累计 {s['elapsed_ms']}ms，已知估算费用 {money}")
    if not stats:
        print("没有符合筛选条件的模型调用。")


if __name__ == "__main__":
    main()
