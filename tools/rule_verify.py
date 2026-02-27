"""
规则验证工具：无需进入游戏即可验证规则触发与冷却逻辑。
"""

import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from analysis.engine import RuleEngine


# 读取 JSON 规则测试输入
def load_cases(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cases" in data and isinstance(data["cases"], list):
        return data["cases"]
    raise ValueError("JSON 根节点必须为数组或包含 cases 的对象")


# 执行规则验证
def run_cases(cases: List[Dict[str, Any]]) -> None:
    engine = RuleEngine()
    mismatches: List[Tuple[int, str]] = []
    for item in cases:
        ts = int(item.get("ts", 0))
        fields = item.get("fields", {})
        alerts = engine.evaluate(fields, ts)
        expect_ids = _get_expect_ids(item)
        if expect_ids is not None:
            actual_ids = [alert.get("id") for alert in alerts]
            if set(actual_ids) != set(expect_ids):
                mismatches.append((ts, f"期望={expect_ids} 实际={actual_ids}"))
        for alert in alerts:
            print(f"{ts} -> {alert}")
    if mismatches:
        print("=== 规则校验不通过 ===")
        for ts, msg in mismatches:
            print(f"{ts} -> {msg}")
        raise SystemExit(1)


# 构造默认测试用例
def build_demo_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    ts = 0
    for _ in range(10):
        cases.append({"ts": ts, "fields": {"idleVillagers": {"value": 0, "conf": 1.0}}})
        ts += 1000
    for _ in range(10):
        cases.append({"ts": ts, "fields": {"idleVillagers": {"value": 6, "conf": 1.0}}})
        ts += 1000
    for _ in range(10):
        cases.append({"ts": ts, "fields": {"idleVillagers": {"value": 0, "conf": 1.0}}})
        ts += 1000
    return cases


# 解析期望 alert id 列表
def _get_expect_ids(item: Dict[str, Any]) -> Optional[List[str]]:
    expect = item.get("expect")
    if expect is None:
        return None
    if isinstance(expect, list):
        return [str(x) for x in expect]
    return None


# 主入口
def main() -> None:
    if len(sys.argv) > 1:
        cases = load_cases(sys.argv[1])
    else:
        cases = build_demo_cases()
    run_cases(cases)


if __name__ == "__main__":
    main()
