"""
捕获管理器：优先 dxcam，失败降级到 mss。
"""

from typing import Optional

import numpy as np

from capture.dxcam_provider import DxcamProvider
from capture.mss_provider import MssProvider
from utils.logging import get_logger


class CaptureManager:
    # 初始化捕获管理器
    def __init__(self) -> None:
        self.logger = get_logger("backend.capture")
        self.dxcam = DxcamProvider()
        self.mss = MssProvider()
        self.provider: Optional[str] = None

    # 初始化捕获器
    def initialize(self, display_id: Optional[int] = None) -> None:
        if self.dxcam.initialize(display_id=display_id):
            self.provider = "dxcam"
            self.logger.info("捕获提供者: dxcam")
            return
        if self.mss.initialize(display_id=display_id):
            self.provider = "mss"
            self.logger.info("捕获提供者: mss")
            return
        self.provider = None
        self.logger.error("捕获提供者初始化失败")

    # 抓取一帧并返回 BGR 图像
    def capture(self) -> Optional[np.ndarray]:
        if self.provider == "dxcam":
            return self.dxcam.capture_frame()
        if self.provider == "mss":
            return self.mss.capture_frame()
        return None
