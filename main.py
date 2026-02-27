"""
AoE4 HUD 后端入口。
"""

from core.state import BackendState
from utils.logging import setup_logging
from ws.server import WsServer


# 主程序入口
def main() -> None:
    setup_logging()
    state = BackendState()
    server = WsServer(state=state)
    server.start()


if __name__ == "__main__":
    main()
