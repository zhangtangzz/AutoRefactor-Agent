import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.config import settings


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConversationMemory:
    """管理单次会话的多轮对话上下文"""

    def __init__(self, max_turns: int = settings.MAX_CONVERSATION_TURNS):
        self.max_turns = max_turns
        self.messages: List[Message] = []

    def add_user(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self.messages.append(Message(role="assistant", content=content))
        self._trim()

    def _trim(self) -> None:
        # 保留最近 N 轮（一轮 = user + assistant）
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]

    def get_context(self) -> List[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        self.messages = []

    def to_dict(self) -> dict:
        return {
            "max_turns": self.max_turns,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMemory":
        mem = cls(max_turns=data.get("max_turns", settings.MAX_CONVERSATION_TURNS))
        for m in data.get("messages", []):
            mem.messages.append(Message(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", ""),
            ))
        return mem
