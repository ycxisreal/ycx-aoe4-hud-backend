"""
消息协议封装。
"""

import time
from typing import Any, Dict


# 构建通用消息结构
def make_message(msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": msg_type,
        "version": 1,
        "ts": int(time.time() * 1000),
        "payload": payload,
    }


# 构建状态消息
def make_status(state: str, message: str | None = None, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"state": state}
    if message is not None:
        payload["message"] = message
    if details is not None:
        payload["details"] = details
    return make_message("BACKEND_STATUS", payload)
