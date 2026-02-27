"""
系统 DPI 缩放读取。
"""

import ctypes


# 获取系统 DPI 缩放比例
def get_system_dpi_scale() -> float:
    try:
        user32 = ctypes.windll.user32
        dpi = user32.GetDpiForSystem()
        if dpi <= 0:
            return 1.0
        return float(dpi) / 96.0
    except Exception:
        return 1.0
