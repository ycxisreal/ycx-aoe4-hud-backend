"""
TTS 播放封装（edge-tts）。
"""

import asyncio
import ctypes
import logging
import os
import tempfile
import threading
import uuid
from queue import Empty, Queue
from typing import Optional, Union


DEFAULT_EDGE_PERCENT = "+0%"


class TtsSpeaker:
    # 初始化语音播报器
    def __init__(self) -> None:
        self.queue: Queue[Optional[str]] = Queue()
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.voice = "zh-CN-XiaoxiaoNeural"
        self.edge_rate = DEFAULT_EDGE_PERCENT
        self.edge_volume = DEFAULT_EDGE_PERCENT
        self.logger = logging.getLogger("backend.tts")

    # 启动播报线程
    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    # 停止播报线程
    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self.queue.put(None)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    # 配置语速、音量与音色
    def configure(
        self,
        rate: Optional[Union[int, str]],
        volume: Optional[Union[float, str]],
        voice: Optional[str] = None,
    ) -> None:
        self.edge_rate = _to_edge_rate(rate)
        self.edge_volume = _to_edge_volume(volume)
        if voice:
            self.voice = voice
        self.logger.info(
            "TTS 配置: voice=%s rate=%s volume=%s",
            self.voice,
            self.edge_rate,
            self.edge_volume,
        )

    # 发送需要播报的文本
    def speak(self, text: str) -> bool:
        if not text or not self.running:
            return False
        self.logger.info("TTS 入队: %s", text)
        self.queue.put(text)
        return True

    # 播报线程循环
    def _loop(self) -> None:
        try:
            import edge_tts
        except Exception as exc:
            self.logger.error("edge-tts 初始化失败: %s", str(exc))
            return

        while self.running:
            try:
                item = self.queue.get(timeout=0.5)
            except Empty:
                continue

            if item is None:
                break

            text = item
            try:
                self.logger.info("TTS 播报: %s", text)
                self._speak_once(edge_tts, text)
                self.logger.info("TTS 播报完成: %s", text)
            except Exception as exc:
                self.logger.error("TTS 播报失败: %s", str(exc))

    # 单次播报：先合成 mp3，再通过系统播放器同步播放
    def _speak_once(self, edge_tts_module, text: str) -> None:
        if os.name != "nt":
            raise RuntimeError("edge-tts 播放当前仅实现 Windows")

        temp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_path = temp_file.name

            communicate = edge_tts_module.Communicate(
                text=text,
                voice=self.voice,
                rate=self.edge_rate,
                volume=self.edge_volume,
            )
            asyncio.run(communicate.save(temp_path))
            _play_mp3_windows(temp_path)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


# 将前端 rate 转成 edge-tts 的百分比字符串
def _to_edge_rate(rate: Optional[Union[int, str]]) -> str:
    if rate is None:
        return DEFAULT_EDGE_PERCENT
    if isinstance(rate, str):
        return _normalize_edge_percent(rate)

    # 兼容旧参数：pyttsx3 语速常用 150，映射为 edge-tts 百分比
    percent = int(round((int(rate) - 150) / 150 * 100))
    percent = max(-90, min(100, percent))
    return f"{percent:+d}%"


# 将前端 volume 转成 edge-tts 的百分比字符串
def _to_edge_volume(volume: Optional[Union[float, str]]) -> str:
    if volume is None:
        return DEFAULT_EDGE_PERCENT
    if isinstance(volume, str):
        return _normalize_edge_percent(volume)

    percent = int(round((float(volume) - 1.0) * 100))
    percent = max(-100, min(100, percent))
    return f"{percent:+d}%"


# 规范化 edge-tts 百分比字符串
def _normalize_edge_percent(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return DEFAULT_EDGE_PERCENT
    if cleaned.endswith("%"):
        return cleaned if cleaned.startswith(("+", "-")) else f"+{cleaned}"
    return DEFAULT_EDGE_PERCENT


# 通过 Windows MCI 同步播放 mp3
def _play_mp3_windows(path: str) -> None:
    alias = f"aoe4_hud_tts_{uuid.uuid4().hex}"
    _mci_send(f'open "{path}" type mpegvideo alias {alias}')
    try:
        _mci_send(f"play {alias} wait")
    finally:
        try:
            _mci_send(f"close {alias}")
        except Exception:
            pass


# 执行一条 MCI 命令并在失败时返回详细错误
def _mci_send(command: str) -> None:
    error_code = ctypes.windll.winmm.mciSendStringW(command, None, 0, 0)
    if error_code == 0:
        return
    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.winmm.mciGetErrorStringW(error_code, buffer, len(buffer))
    message = buffer.value or f"code={error_code}"
    raise RuntimeError(f"MCI 执行失败: {command}; error={message}")
