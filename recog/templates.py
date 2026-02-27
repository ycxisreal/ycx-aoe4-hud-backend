"""
模板加载与归一化。
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class TemplateSet:
    name: str
    templates: Dict[str, object]


class TemplateStore:
    # 初始化模板仓库
    def __init__(self) -> None:
        self.current: TemplateSet | None = None

    # 加载模板集
    def load(self, name: str, path: str) -> None:
        self.current = TemplateSet(name=name, templates={})
