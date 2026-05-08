import json
from typing import AsyncIterator, List, Optional

from langchain_core.documents import Document

from app.agent.conversation import ConversationMemory
from app.config import settings
from app.document.processor import DocumentProcessor
from app.document.vector_store import VectorStoreManager


SYSTEM_PROMPT = """你是一个专业的企业内部智能问答助手。你的职责是：

1. 根据提供的文档内容回答用户问题，确保答案准确、简洁
2. 如果检索到的文档包含相关信息，基于文档内容回答，并注明信息来源
3. 如果检索内容不足以回答问题，诚实告知用户，并建议补充相关文档
4. 对于需要操作步骤的问题，提供清晰的步骤说明
5. 回答使用中文，保持专业友好的语气

注意：你的知识仅限于提供的文档内容，不要编造不存在的信息。"""


class QAAgent:
    """基于 RAG 的智能问答 Agent"""

    def __init__(
        self,
        vector_store: Optional[VectorStoreManager] = None,
        conversation: Optional[ConversationMemory] = None,
    ):
        self.vector_store = vector_store or VectorStoreManager()
        self.conversation = conversation or ConversationMemory()
        self.processor = DocumentProcessor()

    def _build_context(self, question: str) -> str:
        """构建 RAG 上下文：检索相关文档块"""
        docs = self.vector_store.search(question, top_k=settings.TOP_K_RETRIEVAL)
        if not docs:
            return ""

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            parts.append(f"[文档{i}] 来源: {source}\n{doc.page_content}")
        return "\n\n".join(parts)

    def _build_messages(
        self,
        question: str,
        context: str,
        stream: bool = False,
    ) -> List[dict]:
        """构建发给 Claude 的消息列表"""
        messages: list[dict] = [{"role": "user", "content": SYSTEM_PROMPT}]

        # 注入对话历史
        history = self.conversation.get_context()
        if history:
            messages.extend(history)

        # 构建当前问题
        if context:
            user_message = (
                f"请根据以下参考文档内容回答问题。\n\n"
                f"=== 参考文档 ===\n{context}\n=== 文档结束 ===\n\n"
                f"问题: {question}"
            )
        else:
            user_message = (
                f"问题: {question}\n\n"
                f"注意: 当前没有找到相关文档，请根据你的通用知识回答，"
                f"并建议用户上传相关文档以获得更准确的答案。"
            )

        messages.append({"role": "user", "content": user_message})
        return messages

    async def ask(self, question: str) -> dict:
        """同步问答：返回完整答案"""
        self.conversation.add_user(question)
        context = self._build_context(question)
        messages = self._build_messages(question, context)

        answer = await self._call_claude(messages)
        self.conversation.add_assistant(answer)

        return {
            "question": question,
            "answer": answer,
            "sources": self._extract_sources(context),
            "has_context": bool(context),
            "conversation_length": len(self.conversation.messages),
        }

    async def ask_stream(self, question: str) -> AsyncIterator[str]:
        """流式问答：逐步返回答案token"""
        self.conversation.add_user(question)
        context = self._build_context(question)
        messages = self._build_messages(question, context)

        full_answer = []
        async for token in self._call_claude_stream(messages):
            full_answer.append(token)
            yield token

        self.conversation.add_assistant("".join(full_answer))

    async def _call_claude(self, messages: List[dict]) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY 未配置，请在 .env 文件中设置有效的 Claude API Key"
            )
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
        )
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[m for m in messages if m["role"] != "system"],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""

    async def _call_claude_stream(self, messages: List[dict]) -> AsyncIterator[str]:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY 未配置，请在 .env 文件中设置有效的 Claude API Key"
            )
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
        )
        async with client.messages.stream(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[m for m in messages if m["role"] != "system"],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def _extract_sources(self, context: str) -> List[str]:
        if not context:
            return []
        sources = set()
        for line in context.split("\n"):
            if line.startswith("[文档") and "来源:" in line:
                src = line.split("来源:", 1)[1].strip()
                sources.add(src)
        return sorted(sources) if sources else ["无相关文档"]

    def clear_conversation(self) -> None:
        self.conversation.clear()

    def get_conversation(self) -> dict:
        return self.conversation.to_dict()
