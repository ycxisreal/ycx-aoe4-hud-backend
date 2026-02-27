"""
TTS 播放封装。
"""

from queue import Queue


class TtsSpeaker:
    # 初始化语音播报器
    def __init__(self) -> None:
        self.queue: Queue[str] = Queue()

    # 发送需要播报的文本
    def speak(self, text: str) -> None:
        self.queue.put(text)
