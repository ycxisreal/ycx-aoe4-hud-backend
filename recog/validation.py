"""
合法性校验。
"""

from typing import Any, Dict, Optional


class FieldValidator:
    # 初始化校验器
    def __init__(self) -> None:
        self.last_timer_seconds: Optional[int] = None
        self.last_numbers: Dict[str, int] = {}

    # 校验识别字段
    def validate(self, fields: Dict[str, Any]) -> Dict[str, Optional[str]]:
        ok = True
        reason = None
        timer = fields.get("timer")
        if timer:
            seconds = _timer_to_seconds(timer.get("value"))
            if seconds is None:
                ok = False
                reason = "timer_invalid"
            elif self.last_timer_seconds is not None and seconds + 2 < self.last_timer_seconds:
                ok = False
                reason = "timer_regression"
            else:
                self.last_timer_seconds = seconds

        population = fields.get("population")
        if population:
            current = population.get("current")
            capacity = population.get("capacity")
            if (current is None) != (capacity is None):
                ok = False
                reason = "population_invalid"
            elif current is not None and capacity is not None:
                if current < 0 or capacity <= 0 or current > capacity:
                    ok = False
                    reason = "population_invalid"

        numeric_fields = _flatten_numeric(fields)
        for key, value in numeric_fields.items():
            if value < 0:
                ok = False
                reason = "value_negative"
                break
            if key in self.last_numbers and abs(value - self.last_numbers[key]) > 99999:
                ok = False
                reason = "value_jump"
                break
            self.last_numbers[key] = value

        return {"ok": ok, "reason": reason}


# 解析计时器字符串为秒
def _timer_to_seconds(value: Optional[str]) -> Optional[int]:
    if not value or ":" not in value:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    if not (parts[0].isdigit() and parts[1].isdigit()):
        return None
    minutes = int(parts[0])
    seconds = int(parts[1])
    if seconds >= 60:
        return None
    return minutes * 60 + seconds


# 展平数字字段为 key -> value
def _flatten_numeric(fields: Dict[str, Any]) -> Dict[str, int]:
    output: Dict[str, int] = {}
    idle = fields.get("idleVillagers")
    if idle and idle.get("value") is not None:
        output["idleVillagers"] = int(idle["value"])

    resources = fields.get("resources", {})
    for key, item in resources.items():
        if item and item.get("value") is not None:
            output[f"resources.{key}"] = int(item["value"])

    gatherers = fields.get("gatherers", {})
    for key, item in gatherers.items():
        if item and item.get("value") is not None:
            output[f"gatherers.{key}"] = int(item["value"])

    return output
