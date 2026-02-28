"""
规则集合。
"""

from typing import Any, Dict, List


class IdleVillagerRule:
    # 初始化闲置村民规则
    def __init__(self, threshold: int = 0, cooldown_ms: int = 15000) -> None:
        self.threshold = threshold
        self.cooldown_ms = cooldown_ms

    # 评估规则
    def evaluate(self, fields: Dict[str, Any], ts: int) -> List[Dict[str, Any]]:
        idle = fields.get("idleVillagers")
        value = idle.get("value") if idle else None
        if value is None:
            return []
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return []
        if numeric <= self.threshold:
            return []
        # 规则仅表达“当前命中”，重复频率由 RuleEngine 冷却统一控制
        return [
            {
                "id": "idle_villager",
                "level": "warn",
                "text": "有闲置村民",
                "cooldownMs": self.cooldown_ms,
            }
        ]
