"""
WebSocket 服务端。
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from core.state import BackendState
from ws.protocol import make_status


MessageHandler = Callable[[Dict[str, Any], WebSocketServerProtocol], Awaitable[None]]


class WsServer:
    # 初始化服务端
    def __init__(self, state: BackendState, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.logger = logging.getLogger("backend.ws")
        self.state = state
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server: Optional[websockets.server.Serve] = None
        self.on_message: Optional[MessageHandler] = None

    # 启动服务端
    async def start(self, on_message: MessageHandler) -> None:
        self.on_message = on_message
        self.server = await websockets.serve(self._handler, self.host, self.port)
        self.logger.info("WS 服务启动 %s:%s", self.host, self.port)

    # 停止服务端
    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WS 服务已停止")

    # 广播消息
    async def broadcast(self, payload: Dict[str, Any]) -> None:
        if not self.clients:
            return
        data = json.dumps(payload, ensure_ascii=False)
        await asyncio.gather(*(client.send(data) for client in list(self.clients)), return_exceptions=True)
        self.logger.debug("WS 广播类型=%s", payload.get("type"))

    # 发送单个消息
    async def send(self, client: WebSocketServerProtocol, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False)
        await client.send(data)
        self.logger.debug("WS 发送类型=%s", payload.get("type"))

    # 内部处理连接
    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        self.clients.add(websocket)
        self.logger.info("WS 客户端连接，总数=%d", len(self.clients))
        try:
            status = make_status(self.state.state, self.state.message, self.state.details)
            await self.send(websocket, status)
            async for message in websocket:
                try:
                    data = json.loads(message)
                except Exception:
                    continue
                if self.on_message is not None:
                    await self.on_message(data, websocket)
        finally:
            self.clients.discard(websocket)
            self.logger.info("WS 客户端断开，总数=%d", len(self.clients))
