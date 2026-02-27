"""
多帧稳定化。
"""

from collections import deque
from typing import Deque, Dict, Any


class FieldSmoother:
    # 初始化稳定器
    def __init__(self, window_size: int = 7) -> None:
        self.window_size = window_size
        self.buffers: Dict[str, Deque[Any]] = {}

    # 推入新值并输出稳定结果
    def push(self, key: str, value: Any) -> Any:
        if key not in self.buffers:
            self.buffers[key] = deque(maxlen=self.window_size)
        self.buffers[key].append(value)
        return value
