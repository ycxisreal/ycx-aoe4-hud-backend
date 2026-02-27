"""
识别流水线。
"""

from typing import Any, Dict, List, Optional

import numpy as np

from recog.classifier import classify_char
from recog.preprocess import preprocess_roi
from recog.segment import segment_chars
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
            binary, _ = preprocess_roi(cropped, roi.kind)
            boxes = segment_chars(binary, roi.kind)
            chars = [_extract_char(binary, box) for box in boxes]
            template_name = _select_template_name(roi.kind, self.kind_map)
            template_set = self.template_store.get(template_name)
            classified = [classify_char(c, template_set) for c in chars]
            parsed = _parse_classified(classified, roi.kind)
            results[roi.kind] = parsed
        return results


# 裁剪 ROI 区域
def _crop(frame: np.ndarray, rect) -> np.ndarray:
    x = max(0, rect.x)
    y = max(0, rect.y)
    w = max(1, rect.w)
    h = max(1, rect.h)
    return frame[y : y + h, x : x + w]


# 提取字符图像
def _extract_char(binary: np.ndarray, box) -> np.ndarray:
    x, y, w, h = box
    return binary[y : y + h, x : x + w]


# 解析分类结果
def _parse_classified(classified: List[Dict[str, Optional[float]]], kind: str) -> Dict[str, Any]:
    chars = []
    confs = []
    for item in classified:
        char = item.get("char")
        if char is None:
            continue
        chars.append(":" if char == "colon" else char)
        conf = float(item.get("score", 0.0)) - float(item.get("second_score", 0.0))
        confs.append(max(0.0, conf))

    text = "".join(chars)
    conf = float(sum(confs) / len(confs)) if confs else 0.0

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


# 根据 kind 选择模板集
def _select_template_name(kind: str, kind_map: Dict[str, str]) -> Optional[str]:
    if kind in kind_map:
        return kind_map[kind]
    for pattern, name in kind_map.items():
        if pattern.endswith("*") and kind.startswith(pattern[:-1]):
            return name
    return kind_map.get("default")
