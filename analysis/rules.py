"""
规则集合。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# 规则输出级别
LEVEL_WARN = "warn"


@dataclass
class AlertConfig:
    # 告警基础配置
    rule_id: str
    text: str
    level: str = LEVEL_WARN
    hold_ms: int = 0
    cooldown_base_ms: int = 0
    cooldown_accum_ms: int = 0


class StatefulRule:
    """
    通用状态规则：
    1. 条件连续满足 hold_ms 后才允许触发；
    2. 支持基础冷却 + 累加冷却；
    3. 条件不满足时重置内部状态（含累加冷却）。
    """

    # 初始化状态规则
    def __init__(self, config: AlertConfig) -> None:
        self.config = config
        self.hold_start_ts: Optional[int] = None
        self.next_fire_ts: int = 0
        self.cooldown_extra_ms: int = 0

    # 评估规则
    def evaluate(self, fields: Dict[str, Any], ts: int) -> List[Dict[str, Any]]:
        if not self._is_satisfied(fields):
            self._reset()
            return []

        if self.config.hold_ms > 0:
            if self.hold_start_ts is None:
                self.hold_start_ts = ts
                return []
            if ts - self.hold_start_ts < self.config.hold_ms:
                return []

        if ts < self.next_fire_ts:
            return []

        cooldown_ms = self.config.cooldown_base_ms + self.cooldown_extra_ms
        self.next_fire_ts = ts + cooldown_ms
        if self.config.cooldown_accum_ms > 0:
            self.cooldown_extra_ms += self.config.cooldown_accum_ms

        return [
            {
                "id": self.config.rule_id,
                "level": self.config.level,
                "text": self.config.text,
                "cooldownMs": cooldown_ms,
            }
        ]

    # 条件不满足时重置状态
    def _reset(self) -> None:
        self.hold_start_ts = None
        self.next_fire_ts = 0
        self.cooldown_extra_ms = 0

    # 子类实现具体条件
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        raise NotImplementedError


class TimePointRule:
    # 初始化时间点单次提醒规则
    def __init__(self, rule_id: str, target_seconds: int, text: str) -> None:
        self.rule_id = rule_id
        self.target_seconds = target_seconds
        self.text = text
        self.fired = False

    # 评估规则
    def evaluate(self, fields: Dict[str, Any], ts: int) -> List[Dict[str, Any]]:
        del ts
        game_seconds = _get_game_seconds(fields)
        # 计时器无效或回退到阈值以下时，视为进入新对局并重置标记
        if game_seconds is None or game_seconds < self.target_seconds:
            self.fired = False
            return []
        if self.fired:
            return []
        self.fired = True
        return [
            {
                "id": self.rule_id,
                "level": LEVEL_WARN,
                "text": self.text,
                "cooldownMs": 0,
            }
        ]


class IdleVillagerRule(StatefulRule):
    # 初始化闲置村民规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="idle_villager",
                text="有闲置村民",
                hold_ms=0,
                cooldown_base_ms=15000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        idle_v = _get_idle(fields)
        return idle_v >= 1


class StoneCastleReadyRule(StatefulRule):
    # 初始化石头满足城堡建造规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="stone_castle_ready",
                text="石头满足城堡建造",
                hold_ms=6000,
                cooldown_base_ms=120000,
                cooldown_accum_ms=15000,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        stone = _get_resource(fields, "stone")
        return stone > 900


class WoodHighMidGameRule(StatefulRule):
    # 初始化 09:00-15:00 木头偏高规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="wood_high_mid_game",
                text="木头资源偏高",
                hold_ms=12000,
                cooldown_base_ms=45000,
                cooldown_accum_ms=15000,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 9 * 60, 15 * 60):
            return False
        wood = _get_resource(fields, "wood")
        food = _get_resource(fields, "food")
        gold = _get_resource(fields, "gold")
        return wood > 1000 and wood > max(food, gold) * 1.6


class GoldHighEarlyRule(StatefulRule):
    # 初始化 08:00-12:00 黄金偏高规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="gold_high_early",
                text="黄金资源偏高",
                hold_ms=5000,
                cooldown_base_ms=35000,
                cooldown_accum_ms=10000,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 8 * 60, 12 * 60):
            return False
        gold = _get_resource(fields, "gold")
        food = _get_resource(fields, "food")
        total_workers = _get_total_workers(fields)
        if total_workers <= 0:
            return False
        gold_w = _get_gatherer(fields, "gold")
        return gold > 1000 and gold > food * 1.3 and (gold_w / total_workers) >= 0.30


class FoodHighMidGameRule(StatefulRule):
    # 初始化 09:00-15:00 食物偏高规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="food_high_mid_game",
                text="食物资源偏高",
                hold_ms=12000,
                cooldown_base_ms=30000,
                cooldown_accum_ms=15000,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 9 * 60, 15 * 60):
            return False
        food = _get_resource(fields, "food")
        wood = _get_resource(fields, "wood")
        gold = _get_resource(fields, "gold")
        total_workers = _get_total_workers(fields)
        if total_workers <= 0:
            return False
        food_w = _get_gatherer(fields, "food")
        return food > max(wood, gold) * 1.5 and (food_w / total_workers) >= 0.45


class FoodLowEarlyRule(StatefulRule):
    # 初始化 07:00-12:00 食物偏低规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="food_low_early",
                text="食物获取量偏少",
                hold_ms=15000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 7 * 60, 12 * 60):
            return False
        food = _get_resource(fields, "food")
        return food < 300


class GoldLowEarlyRule(StatefulRule):
    # 初始化 07:00-12:00 黄金偏低规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="gold_low_early",
                text="黄金获取量偏少",
                hold_ms=15000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 7 * 60, 12 * 60):
            return False
        gold = _get_resource(fields, "gold")
        return gold < 200


class NoGoldGatherLateRule(StatefulRule):
    # 初始化 06:00 以后无采金且黄金偏低规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="no_gold_gather_late",
                text="当前没有采金，注意黄金来源",
                hold_ms=20000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 6 * 60, None):
            return False
        gold = _get_resource(fields, "gold")
        gold_w = _get_gatherer(fields, "gold")
        return gold_w == 0 and gold < 500


class WoodWorkerRatioRule(StatefulRule):
    # 初始化木材采集占比预警规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="wood_worker_ratio_high",
                text="木材村民数占比已达 50%",
                hold_ms=10000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 9 * 60, 15 * 60):
            return False
        total_workers = _get_total_workers(fields)
        if total_workers <= 0:
            return False
        wood_w = _get_gatherer(fields, "wood")
        return (wood_w / total_workers) > 0.50


class FoodWorkerRatioRule(StatefulRule):
    # 初始化食物采集占比预警规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="food_worker_ratio_high",
                text="食物村民数占比已达 50%",
                hold_ms=10000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 9 * 60, 15 * 60):
            return False
        total_workers = _get_total_workers(fields)
        if total_workers <= 0:
            return False
        food_w = _get_gatherer(fields, "food")
        return (food_w / total_workers) > 0.50


class GoldWorkerRatioRule(StatefulRule):
    # 初始化黄金采集占比预警规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="gold_worker_ratio_high",
                text="黄金村民数占比已达 50%",
                hold_ms=10000,
                cooldown_base_ms=90000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 9 * 60, 15 * 60):
            return False
        total_workers = _get_total_workers(fields)
        if total_workers <= 0:
            return False
        gold_w = _get_gatherer(fields, "gold")
        return (gold_w / total_workers) > 0.50


class WoodOverflowLateRule(StatefulRule):
    # 初始化 15:00 以后木材过剩规则
    def __init__(self) -> None:
        super().__init__(
            AlertConfig(
                rule_id="wood_overflow_late",
                text="木材资源过剩严重",
                hold_ms=15000,
                cooldown_base_ms=120000,
                cooldown_accum_ms=0,
            )
        )

    # 判断条件是否满足
    def _is_satisfied(self, fields: Dict[str, Any]) -> bool:
        if not _in_game_window(fields, 15 * 60, None):
            return False
        wood = _get_resource(fields, "wood")
        food = _get_resource(fields, "food")
        gold = _get_resource(fields, "gold")
        return wood > max(food, gold) * 1.5


# 构建完整规则集合
def build_rules() -> List[Any]:
    return [
        IdleVillagerRule(),
        StoneCastleReadyRule(),
        WoodHighMidGameRule(),
        GoldHighEarlyRule(),
        FoodHighMidGameRule(),
        FoodLowEarlyRule(),
        GoldLowEarlyRule(),
        NoGoldGatherLateRule(),
        WoodWorkerRatioRule(),
        FoodWorkerRatioRule(),
        GoldWorkerRatioRule(),
        WoodOverflowLateRule(),
        TimePointRule("timeline_1200", 12 * 60, "建议检查对面二金位置"),
        TimePointRule("timeline_1500", 15 * 60, "建议检查资源配比情况"),
    ]


# 读取资源值
def _get_resource(fields: Dict[str, Any], key: str) -> int:
    resources = fields.get("resources", {})
    item = resources.get(key) if isinstance(resources, dict) else None
    return _to_int(item.get("value") if isinstance(item, dict) else None)


# 读取采集村民值
def _get_gatherer(fields: Dict[str, Any], key: str) -> int:
    gatherers = fields.get("gatherers", {})
    item = gatherers.get(key) if isinstance(gatherers, dict) else None
    return _to_int(item.get("value") if isinstance(item, dict) else None)


# 读取闲置村民值
def _get_idle(fields: Dict[str, Any]) -> int:
    idle = fields.get("idleVillagers")
    if not isinstance(idle, dict):
        return 0
    return _to_int(idle.get("value"))


# 计算总村民数
def _get_total_workers(fields: Dict[str, Any]) -> int:
    return (
        _get_gatherer(fields, "food")
        + _get_gatherer(fields, "wood")
        + _get_gatherer(fields, "gold")
        + _get_gatherer(fields, "stone")
        + _get_idle(fields)
    )


# 判断是否位于指定游戏时间窗
def _in_game_window(fields: Dict[str, Any], start_seconds: Optional[int], end_seconds: Optional[int]) -> bool:
    game_seconds = _get_game_seconds(fields)
    if game_seconds is None:
        return False
    if start_seconds is not None and game_seconds < start_seconds:
        return False
    if end_seconds is not None and game_seconds >= end_seconds:
        return False
    return True


# 读取游戏计时器秒数
def _get_game_seconds(fields: Dict[str, Any]) -> Optional[int]:
    timer = fields.get("timer")
    if not isinstance(timer, dict):
        return None
    value = timer.get("value")
    if not isinstance(value, str) or ":" not in value:
        return None
    parts = value.split(":")
    if len(parts) != 2 or (not parts[0].isdigit()) or (not parts[1].isdigit()):
        return None
    minutes = int(parts[0])
    seconds = int(parts[1])
    if seconds >= 60:
        return None
    return minutes * 60 + seconds


# 安全转整数
def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
