"""
调试输出工具。
"""

from pathlib import Path
from typing import Union

import cv2
import numpy as np


# 保存调试数据
def dump_debug(data: bytes, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


# 保存调试图像
def dump_image(image: np.ndarray, path: Union[str, Path]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(target), image)
