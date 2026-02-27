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
    if _use_projection(kind):
        boxes = _segment_by_projection(image, kind)
        if boxes:
            return boxes
    return _segment_by_components(image, kind)


# 判断是否使用投影切分
def _use_projection(kind: str) -> bool:
    return kind in ("idle",) or kind.startswith("res_") or kind.startswith("gather_")


# 通过连通域切分
def _segment_by_components(image: np.ndarray, kind: str) -> List[Tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    total_area = max(1, height * width)
    min_area = max(5, int(total_area * (0.00025 if kind == "timer" else 0.0008)))
    max_area = int(total_area * 0.2)

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(image, connectivity=8)
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


# 通过垂直投影切分（更适合数字串）
def _segment_by_projection(image: np.ndarray, kind: str) -> List[Tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    col_sum = (image > 0).sum(axis=0)
    row_sum = (image > 0).sum(axis=1)

    if col_sum.max() == 0:
        return []

    y_indices = np.where(row_sum > 0)[0]
    if y_indices.size == 0:
        return []
    y_min = int(y_indices.min())
    y_max = int(y_indices.max())

    threshold_ratio = 0.12 if kind == "timer" else 0.18
    threshold = max(1, int(col_sum.max() * threshold_ratio))
    mask = col_sum > threshold

    ranges: List[Tuple[int, int]] = []
    start = None
    for i, active in enumerate(mask):
        if active and start is None:
            start = i
        if not active and start is not None:
            ranges.append((start, i - 1))
            start = None
    if start is not None:
        ranges.append((start, len(mask) - 1))

    boxes: List[Tuple[int, int, int, int]] = []
    min_w = max(2, int(width * 0.02))
    min_h = max(5, int(height * 0.4))
    for x_start, x_end in ranges:
        if (x_end - x_start + 1) < min_w:
            continue
        region = image[y_min : y_max + 1, x_start : x_end + 1]
        rows = np.where(region.sum(axis=1) > 0)[0]
        if rows.size == 0:
            continue
        y1 = int(rows.min()) + y_min
        y2 = int(rows.max()) + y_min
        h = y2 - y1 + 1
        w = x_end - x_start + 1
        if h < min_h:
            continue
        boxes.append((x_start, y1, w, h))

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
