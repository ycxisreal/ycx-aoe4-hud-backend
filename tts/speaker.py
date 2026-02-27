"""
TTS 播放封装。
"""

import threading
from queue import Queue
from typing import Optional


class TtsSpeaker:
    # 初始化语音播报器
    def __init__(self) -> None:
        self.queue: Queue[str] = Queue()
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.rate: Optional[int] = None
        self.volume: Optional[float] = None

    # 启动播报线程
    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # 停止播报线程
    def stop(self) -> None:
        self.running = False

    # 设置语速与音量
    def configure(self, rate: Optional[int], volume: Optional[float]) -> None:
        self.rate = rate
        self.volume = volume

    # 发送需要播报的文本
    def speak(self, text: str) -> None:
        self.queue.put(text)

    # 内部播报循环
    def _loop(self) -> None:
        try:
            import pyttsx3
        except Exception:
            return
        engine = pyttsx3.init()
        while self.running:
            text = self.queue.get()
            if self.rate is not None:
                engine.setProperty("rate", self.rate)
            if self.volume is not None:
                engine.setProperty("volume", self.volume)
            engine.say(text)
            engine.runAndWait()
