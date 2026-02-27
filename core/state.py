"""
运行状态管理。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendState:
    state: str = "starting"
    message: Optional[str] = None
    details: dict = field(default_factory=dict)

    # 更新当前状态
    def update(self, state: str, message: Optional[str] = None, details: Optional[dict] = None) -> None:
        self.state = state
        self.message = message
        if details is not None:
            self.details = details
