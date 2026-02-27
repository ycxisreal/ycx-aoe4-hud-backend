"""
模板匹配分类器。
"""

from typing import Dict, Optional

import numpy as np

from recog.templates import TemplateSet, compute_hog, normalize_char


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
    if template_set.samples.size > 0 and template_set.labels:
        best_char, best_score, second_score = _knn_classify(
            normalized, template_set.samples, template_set.labels, template_set.size
        )
    else:
        if template_set.features:
            feat = compute_hog(normalized, template_set.size)
            for key, tmpl_feat in template_set.features.items():
                score = _cosine_score(feat, tmpl_feat)
                if score > best_score:
                    second_score = best_score
                    best_score = score
                    best_char = key
                elif score > second_score:
                    second_score = score
        else:
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


# 余弦相似度
def _cosine_score(vec: np.ndarray, tmpl: np.ndarray) -> float:
    denom = (np.linalg.norm(vec) * np.linalg.norm(tmpl)) + 1e-6
    return float(np.dot(vec, tmpl) / denom)


# KNN 分类
def _knn_classify(
    image: np.ndarray, samples: np.ndarray, labels: list[str], size: tuple[int, int], k: int = 3
) -> tuple[Optional[str], float, float]:
    feat = compute_hog(image, size)
    if samples.size == 0:
        return None, 0.0, 0.0
    norms = (np.linalg.norm(samples, axis=1) * np.linalg.norm(feat)) + 1e-6
    sims = (samples @ feat) / norms
    k = max(1, min(k, sims.shape[0]))
    idx = np.argpartition(-sims, k - 1)[:k]
    score_map: dict[str, float] = {}
    for i in idx:
        label = labels[int(i)]
        score_map[label] = score_map.get(label, 0.0) + float(sims[int(i)])
    sorted_items = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    best_char, best_score = (sorted_items[0][0], sorted_items[0][1]) if sorted_items else (None, 0.0)
    second_score = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    return best_char, best_score, second_score
# 相关系数评分
def _corr_score(image: np.ndarray, template: np.ndarray) -> float:
    image_f = image.astype(np.float32)
    tmpl_f = template.astype(np.float32)
    image_f -= image_f.mean()
    tmpl_f -= tmpl_f.mean()
    denom = (np.linalg.norm(image_f) * np.linalg.norm(tmpl_f)) + 1e-6
    return float((image_f * tmpl_f).sum() / denom)
