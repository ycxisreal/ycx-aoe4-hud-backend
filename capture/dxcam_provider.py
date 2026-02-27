"""
dxcam 捕获封装。
"""

from typing import Optional

import numpy as np

from utils.logging import get_logger


class DxcamProvider:
    # 初始化捕获器
    def __init__(self) -> None:
        self.logger = get_logger("backend.capture.dxcam")
        self.camera = None

    # 初始化捕获设备
    def initialize(self, display_id: Optional[int] = None) -> bool:
        try:
            import dxcam
        except Exception:
            self.camera = None
            return False

        try:
            self.camera = dxcam.create(output_color="BGR", output_idx=display_id)
            return self.camera is not None
        except Exception:
            self.camera = None
            return False

    # 抓取当前帧
    def capture_frame(self) -> Optional[np.ndarray]:
        if self.camera is None:
            return None
        try:
            frame = self.camera.grab()
            if frame is None:
                return None
            return frame
        except Exception:
            return None
