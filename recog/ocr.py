"""
OCR 识别封装（Tesseract）。
"""

from typing import Optional, Tuple

import cv2
import numpy as np


# OCR 读取 ROI 文本
def ocr_read(image: np.ndarray, kind: str) -> Tuple[Optional[str], float]:
    """
    处理说明：
    1. 灰度化与二值化
    2. 反色为黑字白底
    3. 放大增强可读性
    4. 使用 Tesseract 进行识别
    """
    try:
        import pytesseract
    except Exception:
        return None, 0.0

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
    binary = cv2.bitwise_not(binary)

    scale = 2
    h, w = binary.shape[:2]
    resized = cv2.resize(binary, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    if kind == "timer":
        whitelist = "0123456789:"
        psm = 7
    else:
        whitelist = "0123456789"
        psm = 7

    config = f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}"
    text = pytesseract.image_to_string(resized, config=config)
    if text is None:
        return None, 0.0
    cleaned = _clean_text(text, whitelist)
    if not cleaned:
        return None, 0.0
    return cleaned, 1.0


# 清洗 OCR 文本
def _clean_text(text: str, whitelist: str) -> str:
    allowed = set(whitelist)
    cleaned = "".join(ch for ch in text if ch in allowed)
    return cleaned.strip()
