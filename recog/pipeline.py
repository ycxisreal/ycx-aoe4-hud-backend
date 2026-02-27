"""
识别流水线。
"""

from typing import Any, Dict, Optional

import numpy as np

from recog.ocr import ocr_read


class RecognizePipeline:
    # 初始化流水线
    def __init__(self) -> None:
        pass

    # 处理一帧并返回识别结果
    def process(self, frame: np.ndarray, rois) -> Dict[str, Any]:
        """
        流水线说明：
        1. ROI 裁剪
        2. OCR 识别
        3. 字段解析
        """
        results: Dict[str, Any] = {}
        for roi in rois:
            cropped = _crop(frame, roi.rect)
            text, conf = ocr_read(cropped, roi.kind)
            parsed = _parse_ocr(text, conf, roi.kind)
            results[roi.kind] = parsed
        return results


# 裁剪 ROI 区域
def _crop(frame: np.ndarray, rect) -> np.ndarray:
    x = max(0, rect.x)
    y = max(0, rect.y)
    w = max(1, rect.w)
    h = max(1, rect.h)
    return frame[y : y + h, x : x + w]


# 解析 OCR 结果
def _parse_ocr(text: Optional[str], conf: float, kind: str) -> Dict[str, Any]:
    if not text:
        return {"value": None, "conf": 0.0}
    if kind == "timer":
        if _valid_timer(text):
            return {"value": text, "conf": conf}
        return {"value": None, "conf": 0.0}
    if text.isdigit():
        return {"value": int(text), "conf": conf}
    return {"value": None, "conf": 0.0}


# 校验计时器格式
def _valid_timer(text: str) -> bool:
    if len(text) < 4 or ":" not in text:
        return False
    parts = text.split(":")
    if len(parts) != 2:
        return False
    if not (parts[0].isdigit() and parts[1].isdigit()):
        return False
    if len(parts[1]) != 2:
        return False
    return True

