"""
mss 捕获封装。
"""

from typing import Optional

import numpy as np

from utils.logging import get_logger


class MssProvider:
    # 初始化捕获器
    def __init__(self) -> None:
        self.logger = get_logger("backend.capture.mss")
        self.session = None
        self.monitor = None

    # 初始化捕获设备
    def initialize(self, display_id: Optional[int] = None) -> bool:
        try:
            import mss
        except Exception:
            self.session = None
            self.logger.warning("mss import failed")
            return False

        try:
            self.session = mss.mss()
            monitors = self.session.monitors
            if not monitors:
                self.logger.error("mss no monitors")
                return False
            if display_id is None:
                self.monitor = monitors[0]
            else:
                index = min(max(display_id, 0), len(monitors) - 1)
                self.monitor = monitors[index]
            return True
        except Exception:
            self.session = None
            self.logger.error("mss init failed")
            return False

    # 抓取当前帧
    def capture_frame(self) -> Optional[np.ndarray]:
        if self.session is None or self.monitor is None:
            return None
        try:
            frame = self.session.grab(self.monitor)
            image = np.array(frame)
            if image.size == 0:
                self.logger.debug("mss grab returned empty")
                return None
            return image[:, :, :3]
        except Exception:
            self.logger.warning("mss grab failed")
            return None
