"""
WebSocket 服务端骨架。
"""

from core.state import BackendState
from ws.protocol import make_status


class WsServer:
    # 初始化服务端
    def __init__(self, state: BackendState) -> None:
        self.state = state

    # 启动服务端
    def start(self) -> None:
        self.state.update("ready")
        status = make_status(self.state.state, self.state.message, self.state.details)
        _ = status

    # 停止服务端
    def stop(self) -> None:
        self.state.update("stopped")
