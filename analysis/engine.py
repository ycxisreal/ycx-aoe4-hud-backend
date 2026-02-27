"""
规则引擎。
"""

from analysis.rules import idle_villager_rule


class RuleEngine:
    # 初始化规则引擎
    def __init__(self) -> None:
        self.rules = [idle_villager_rule]

    # 执行所有规则
    def evaluate(self, fields, ts):
        alerts = []
        for rule in self.rules:
            alerts.extend(rule(fields, ts))
        return alerts
