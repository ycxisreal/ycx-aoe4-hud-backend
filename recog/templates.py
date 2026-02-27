"""
模板加载与归一化。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class TemplateSet:
    name: str
    templates: Dict[str, np.ndarray]
    features: Dict[str, np.ndarray]
    samples: np.ndarray
    labels: List[str]
    size: Tuple[int, int]


class TemplateStore:
    # 初始化模板仓库
    def __init__(self) -> None:
        self.current: Optional[TemplateSet] = None
        self.sets: Dict[str, TemplateSet] = {}

    # 加载模板集
    def load(self, name: str, path: str, size: Tuple[int, int] = (32, 32)) -> bool:
        template_dir = Path(path)
        templates: Dict[str, np.ndarray] = {}
        features: Dict[str, np.ndarray] = {}
        sample_list: List[np.ndarray] = []
        label_list: List[str] = []
        for key in [str(i) for i in range(10)] + ["colon"]:
            file_path = template_dir / f"{key}.png"
            if not file_path.exists():
                continue
            image = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue
            normalized = normalize_char(image, size)
            templates[key] = normalized
            features[key] = compute_hog(normalized, size)
            augmented = augment_images(normalized)
            for item in augmented:
                sample_list.append(compute_hog(item, size))
                label_list.append(key)
        if not templates:
            return False
        samples = np.stack(sample_list, axis=0) if sample_list else np.zeros((0, 1), dtype=np.float32)
        template_set = TemplateSet(
            name=name,
            templates=templates,
            features=features,
            samples=samples,
            labels=label_list,
            size=size,
        )
        self.sets[name] = template_set
        if self.current is None:
            self.current = template_set
        return True

    # 判断模板集是否可用
    def is_ready(self) -> bool:
        return any(len(item.templates) > 0 for item in self.sets.values()) or (
            self.current is not None and len(self.current.templates) > 0
        )

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


# 计算 HOG 特征
def compute_hog(image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """
    HOG 特征说明：
    1. 输入必须为固定大小灰度图
    2. 返回一维特征向量
    """
    w, h = size
    hog = cv2.HOGDescriptor(
        _winSize=(w, h),
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9,
    )
    feat = hog.compute(image)
    return feat.flatten()


# 模板增强生成
def augment_images(image: np.ndarray) -> List[np.ndarray]:
    """
    增强说明：
    1. 轻微平移与缩放
    2. 轻度膨胀/腐蚀
    3. 轻度模糊
    """
    h, w = image.shape[:2]
    variants: List[np.ndarray] = [image]

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        mat = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted = cv2.warpAffine(image, mat, (w, h), borderValue=0)
        variants.append(shifted)

    for scale in [0.9, 1.0, 1.1]:
        mat = cv2.getRotationMatrix2D((w / 2, h / 2), 0, scale)
        scaled = cv2.warpAffine(image, mat, (w, h), borderValue=0)
        variants.append(scaled)

    kernel = np.ones((2, 2), np.uint8)
    variants.append(cv2.dilate(image, kernel, iterations=1))
    variants.append(cv2.erode(image, kernel, iterations=1))
    variants.append(cv2.GaussianBlur(image, (3, 3), 0))

    return variants
