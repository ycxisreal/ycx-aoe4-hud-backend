"""
调试输出工具。
"""

from pathlib import Path


# 保存调试图像或数据
def dump_debug(data: bytes, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
