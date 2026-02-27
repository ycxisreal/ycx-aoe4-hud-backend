"""
模板加载与归一化。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np


@dataclass
class TemplateSet:
    name: str
    templates: Dict[str, np.ndarray]
    size: Tuple[int, int]


class TemplateStore:
    # 初始化模板仓库
    def __init__(self) -> None:
        self.current: Optional[TemplateSet] = None
        self.sets: Dict[str, TemplateSet] = {}

    # 加载模板集
    def load(self, name: str, path: str, size: Tuple[int, int] = (32, 32)) -> None:
        template_dir = Path(path)
        templates: Dict[str, np.ndarray] = {}
        for key in [str(i) for i in range(10)] + ["colon"]:
            file_path = template_dir / f"{key}.png"
            if not file_path.exists():
                continue
            image = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            templates[key] = normalize_char(image, size)
        template_set = TemplateSet(name=name, templates=templates, size=size)
        self.current = template_set
        self.sets[name] = template_set

    # 判断模板集是否可用
    def is_ready(self) -> bool:
        return self.current is not None and len(self.current.templates) > 0

    # 获取指定模板集
    def get(self, name: Optional[str]) -> Optional[TemplateSet]:
        if name is None:
            return self.current
        return self.sets.get(name)


# 归一化字符图像
def normalize_char(image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """
    归一化说明：
    1. 二值化与前景统一
    2. 缩放到固定大小
    3. 居中填充
    """
    _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)

    target_w, target_h = size
    h, w = binary.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((target_h, target_w), dtype=np.uint8)

    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((target_h, target_w), dtype=np.uint8)
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas[y : y + new_h, x : x + new_w] = resized
    return canvas
