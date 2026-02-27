"""
运行状态管理。
"""

from dataclasses import dataclass, field
from typing import Optional

from core.config import ConfigSetPayload


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


@dataclass
class RuntimeContext:
    # 初始化运行上下文
    def __init__(self) -> None:
        self.config: Optional[ConfigSetPayload] = None
        self.running: bool = False
        self.last_frame_ts: Optional[int] = None
        self.quality_ok: bool = True
        self.quality_reason: Optional[str] = None
