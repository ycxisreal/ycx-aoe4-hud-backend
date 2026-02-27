"""
多帧稳定化。
"""

from collections import Counter, deque
from typing import Deque, Dict, Optional


class FieldSmoother:
    # 初始化稳定器
    def __init__(self, window_size: int = 7) -> None:
        self.window_size = window_size
        self.buffers: Dict[str, Deque[Optional[str]]] = {}

    # 推入新值并输出稳定结果
    def push(self, key: str, value: Optional[str]) -> Optional[str]:
        if key not in self.buffers:
            self.buffers[key] = deque(maxlen=self.window_size)
        self.buffers[key].append(value)
        return self._majority(self.buffers[key])

    # 计算当前窗口多数值
    def _majority(self, buffer: Deque[Optional[str]]) -> Optional[str]:
        values = [v for v in buffer if v is not None]
        if not values:
            return None
        counter = Counter(values)
        return counter.most_common(1)[0][0]
