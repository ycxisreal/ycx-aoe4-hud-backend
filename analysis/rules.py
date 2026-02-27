"""
规则集合。
"""

from typing import Any, Dict, List


class IdleVillagerRule:
    # 初始化闲置村民规则
    def __init__(self, threshold: int = 0, duration_ms: int = 8000) -> None:
        self.threshold = threshold
        self.duration_ms = duration_ms
        self.start_ts: int | None = None

    # 评估规则
    def evaluate(self, fields: Dict[str, Any], ts: int) -> List[Dict[str, Any]]:
        idle = fields.get("idleVillagers")
        value = idle.get("value") if idle else None
        if value is None or value <= self.threshold:
            self.start_ts = None
            return []
        if self.start_ts is None:
            self.start_ts = ts
            return []
        if ts - self.start_ts >= self.duration_ms:
            self.start_ts = ts
            return [
                {
                    "id": "idle_villager",
                    "level": "warn",
                    "text": "有闲置村民",
                    "cooldownMs": 15000,
                }
            ]
        return []
