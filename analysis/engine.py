"""
规则引擎。
"""

from typing import Any, Dict, List

from analysis.rules import build_rules


class RuleEngine:
    # 初始化规则引擎
    def __init__(self) -> None:
        self.rules = build_rules()
        self.cooldowns: Dict[str, int] = {}

    # 执行所有规则
    def evaluate(self, fields: Dict[str, Any], ts: int) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        for rule in self.rules:
            alerts.extend(rule.evaluate(fields, ts))
        return self._apply_cooldowns(alerts, ts)

    # 冷却与节流处理
    def _apply_cooldowns(self, alerts: List[Dict[str, Any]], ts: int) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for alert in alerts:
            alert_id = alert.get("id")
            cooldown = int(alert.get("cooldownMs", 0))
            if alert_id in self.cooldowns and ts - self.cooldowns[alert_id] < cooldown:
                continue
            filtered.append(alert)
            self.cooldowns[alert_id] = ts
        return filtered
