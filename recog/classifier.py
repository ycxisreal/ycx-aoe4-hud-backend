"""
模板匹配分类器。
"""

from typing import Dict, Optional

import numpy as np

from recog.templates import TemplateSet, normalize_char


# 分类单个字符图像
def classify_char(char_image: np.ndarray, template_set: TemplateSet) -> Dict[str, Optional[float]]:
    """
    分类说明：
    1. 归一化到模板尺寸
    2. 计算每个模板的相关系数
    3. 输出最佳字符与置信度
    """
    if template_set is None or len(template_set.templates) == 0:
        return {"char": None, "score": 0.0, "second_score": 0.0}

    normalized = normalize_char(char_image, template_set.size)
    best_char = None
    best_score = -1.0
    second_score = -1.0
    for key, tmpl in template_set.templates.items():
        score = _corr_score(normalized, tmpl)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_char = key
        elif score > second_score:
            second_score = score
    if second_score < 0:
        second_score = 0.0
    return {"char": best_char, "score": float(best_score), "second_score": float(second_score)}


# 相关系数评分
def _corr_score(image: np.ndarray, template: np.ndarray) -> float:
    image_f = image.astype(np.float32)
    tmpl_f = template.astype(np.float32)
    image_f -= image_f.mean()
    tmpl_f -= tmpl_f.mean()
    denom = (np.linalg.norm(image_f) * np.linalg.norm(tmpl_f)) + 1e-6
    return float((image_f * tmpl_f).sum() / denom)
