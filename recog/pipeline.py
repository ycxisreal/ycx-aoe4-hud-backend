"""
识别流水线。
"""

from recog.classifier import classify_char
from recog.preprocess import preprocess_roi
from recog.segment import segment_chars


class RecognizePipeline:
    # 初始化流水线
    def __init__(self) -> None:
        pass

    # 处理一帧并返回识别结果
    def process(self, frame, rois):
        results = {}
        for roi in rois:
            image = preprocess_roi(frame, roi.kind)
            chars = segment_chars(image, roi.kind)
            classified = [classify_char(c, None) for c in chars]
            results[roi.id] = classified
        return results
