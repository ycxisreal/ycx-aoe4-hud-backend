"""
ROI 预处理。
"""

from typing import Tuple

import cv2
import numpy as np


# 预处理单个 ROI 图像
def preprocess_roi(image: np.ndarray, kind: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    预处理流水线说明：
    1. 灰度化与对比度增强
    2. 自适应或 Otsu 二值化
    3. 前景统一为白色（255），背景为黑色（0）
    4. 形态学开运算去噪
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blur = cv2.GaussianBlur(enhanced, (3, 3), 0)

    if kind == "timer":
        _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)

    kernel = np.ones((2, 2), np.uint8)
    denoise = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    if kind != "timer":
        denoise = cv2.morphologyEx(denoise, cv2.MORPH_CLOSE, kernel, iterations=1)
    return denoise, gray
