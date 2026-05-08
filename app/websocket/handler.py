import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.qa_agent import QAAgent
from app.document.vector_store import VectorStoreManager

ws_router = APIRouter()
vector_store = VectorStoreManager()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message, ensure_ascii=False))

    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            try:
                await conn.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                pass


manager = ConnectionManager()


@ws_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 实时问答"""
    await manager.connect(websocket)
    agent = QAAgent(vector_store=vector_store)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                question = payload.get("question", "")
                action = payload.get("action", "ask")

                if action == "clear":
                    agent.clear_conversation()
                    await manager.send_message(
                        {"type": "system", "message": "对话已清除"}, websocket,
                    )
                    continue

                if action == "ask" and question:
                    await manager.send_message(
                        {"type": "thinking", "message": "正在检索相关文档..."}, websocket,
                    )
                    result = await agent.ask(question)
                    await manager.send_message({
                        "type": "answer",
                        "question": result["question"],
                        "answer": result["answer"],
                        "sources": result["sources"],
                        "has_context": result["has_context"],
                    }, websocket)
                else:
                    await manager.send_message(
                        {"type": "error", "message": "请提供有效的问题"}, websocket,
                    )
            except json.JSONDecodeError:
                await manager.send_message(
                    {"type": "error", "message": "无效的JSON格式"}, websocket,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
