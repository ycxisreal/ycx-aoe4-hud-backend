"""
字符切分。
"""

from typing import List, Tuple

import cv2
import numpy as np


# 切分 ROI 中的字符
def segment_chars(image: np.ndarray, kind: str) -> List[Tuple[int, int, int, int]]:
    """
    字符切分说明：
    1. 使用连通域获取候选字符块
    2. 过滤面积异常的噪点
    3. 对冒号可能拆成两个点的情况进行合并
    4. 按 x 坐标排序输出字符框
    """
    height, width = image.shape[:2]
    total_area = max(1, height * width)
    min_area = max(5, int(total_area * (0.0003 if kind == "timer" else 0.0008)))
    max_area = int(total_area * 0.2)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(image, connectivity=8)
    boxes: List[Tuple[int, int, int, int]] = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < min_area or area > max_area:
            continue
        if w < 2 or h < 2:
            continue
        boxes.append((x, y, w, h))

    boxes = _merge_colon_like(boxes, width)
    boxes.sort(key=lambda b: b[0])
    return boxes


# 合并冒号样式的两个小点
def _merge_colon_like(boxes: List[Tuple[int, int, int, int]], width: int) -> List[Tuple[int, int, int, int]]:
    if len(boxes) < 2:
        return boxes
    boxes = sorted(boxes, key=lambda b: b[0])
    merged: List[Tuple[int, int, int, int]] = []
    skip = set()
    for i in range(len(boxes)):
        if i in skip:
            continue
        x1, y1, w1, h1 = boxes[i]
        for j in range(i + 1, len(boxes)):
            if j in skip:
                continue
            x2, y2, w2, h2 = boxes[j]
            if abs((x1 + w1 / 2) - (x2 + w2 / 2)) <= max(2, int(width * 0.01)):
                if y2 > y1 + h1 or y1 > y2 + h2:
                    x = min(x1, x2)
                    y = min(y1, y2)
                    w = max(x1 + w1, x2 + w2) - x
                    h = max(y1 + h1, y2 + h2) - y
                    merged.append((x, y, w, h))
                    skip.add(j)
                    break
        else:
            merged.append((x1, y1, w1, h1))
    return merged
