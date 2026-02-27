"""
mss 捕获封装。
"""


class MssProvider:
    # 初始化捕获器
    def __init__(self) -> None:
        self.session = None

    # 初始化捕获设备
    def initialize(self) -> None:
        self.session = None

    # 抓取当前帧
    def capture_frame(self):
        if self.session is None:
            return None
        return None
