"""
dxcam 捕获封装。
"""


class DxcamProvider:
    # 初始化捕获器
    def __init__(self) -> None:
        self.camera = None

    # 初始化捕获设备
    def initialize(self) -> None:
        self.camera = None

    # 抓取当前帧
    def capture_frame(self):
        if self.camera is None:
            return None
        return None
