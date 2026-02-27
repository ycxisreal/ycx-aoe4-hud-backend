"""
WebSocket 服务端。
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from core.state import BackendState
from ws.protocol import make_status


MessageHandler = Callable[[Dict[str, Any], WebSocketServerProtocol], Awaitable[None]]


class WsServer:
    # 初始化服务端
    def __init__(self, state: BackendState, host: str = "127.0.0.1", port: int = 8765) -> None:
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

    # 停止服务端
    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    # 广播消息
    async def broadcast(self, payload: Dict[str, Any]) -> None:
        if not self.clients:
            return
        data = json.dumps(payload, ensure_ascii=False)
        await asyncio.gather(*(client.send(data) for client in list(self.clients)), return_exceptions=True)

    # 发送单个消息
    async def send(self, client: WebSocketServerProtocol, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False)
        await client.send(data)

    # 内部处理连接
    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        self.clients.add(websocket)
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
