"""
配置模型定义。
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class Rect(BaseModel):
    x: int
    y: int
    w: int
    h: int


class ScreenInfo(BaseModel):
    width: int
    height: int
    dpiScale: Optional[float] = None
    displayId: Optional[int] = None


class RoiExpected(BaseModel):
    charset: Optional[str] = None
    maxLen: Optional[int] = None


class Roi(BaseModel):
    id: str
    name: str
    rect: Rect
    kind: str
    expected: Optional[RoiExpected] = None


class RecognitionConfig(BaseModel):
    enabled: bool = True
    hz: int = Field(default=2, ge=1, le=10)


class TtsConfig(BaseModel):
    enabled: bool = True
    rate: Optional[Union[int, str]] = None
    volume: Optional[Union[float, str]] = None
    voice: Optional[str] = None


class ConfigSetPayload(BaseModel):
    clientId: str
    screen: ScreenInfo
    rois: List[Roi]
    recognition: RecognitionConfig
    tts: Optional[TtsConfig] = None


class WsMessage(BaseModel):
    type: str
    version: int = 1
    ts: int
    payload: dict

    # 解析消息字典
    @staticmethod
    def parse(data: dict) -> "WsMessage":
        return WsMessage(**data)
