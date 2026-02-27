"""
识别流水线。
"""

from typing import Any, Dict, Optional

import numpy as np

from recog.ocr import ocr_read
from recog.templates import TemplateStore


class RecognizePipeline:
    # 初始化流水线
    def __init__(self, template_store: TemplateStore) -> None:
        self.template_store = template_store
        self.kind_map: Dict[str, str] = {}

    # 更新模板映射
    def update_kind_map(self, kind_map: Dict[str, str]) -> None:
        self.kind_map = kind_map

    # 处理一帧并返回识别结果
    def process(self, frame: np.ndarray, rois) -> Dict[str, Any]:
        """
        流水线说明：
        1. ROI 裁剪并预处理
        2. 字符切分与逐字符分类
        3. 拼接与字段解析
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


# 保留接口以兼容旧配置
def _select_template_name(kind: str, kind_map: Dict[str, str]) -> Optional[str]:
    if kind in kind_map:
        return kind_map[kind]
    for pattern, name in kind_map.items():
        if pattern.endswith("*") and kind.startswith(pattern[:-1]):
            return name
    return kind_map.get("default")
