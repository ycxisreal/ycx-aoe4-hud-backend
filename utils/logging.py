"""
日志初始化。
"""

import logging


# 初始化日志系统
def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


# 获取日志实例
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
