import hashlib
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.agent.conversation import ConversationMemory
from app.agent.qa_agent import QAAgent
from app.api.schemas import (
    AskRequest,
    AskResponse,
    ConversationResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
    ErrorResponse,
    HealthResponse,
    LoginRequest,
    TokenResponse,
)
from app.auth.jwt_handler import TokenPayload, create_access_token, get_current_user
from app.auth.rbac import Role, require_permission, require_role
from app.cache.redis_cache import RedisCache
from app.config import settings
from app.document.loader import DocumentLoader
from app.document.processor import DocumentProcessor
from app.document.vector_store import VectorStoreManager

router = APIRouter()

# 全局实例
vector_store = VectorStoreManager()
processor = DocumentProcessor()
redis_cache = RedisCache()

# 本地内存对话存储（Redis不可用时回退）
_local_conversations: dict[str, ConversationMemory] = {}


def _get_or_create_agent(session_id: Optional[str] = None) -> tuple[QAAgent, str]:
    """获取或创建 QA Agent，关联会话"""
    sid = session_id or uuid.uuid4().hex[:12]
    conversation = _local_conversations.get(sid)
    if conversation is None:
        conversation = ConversationMemory()
        _local_conversations[sid] = conversation
    agent = QAAgent(vector_store=vector_store, conversation=conversation)
    return agent, sid


# ==================== 认证 ====================

@router.post("/auth/login", response_model=TokenResponse, tags=["认证"])
async def login(body: LoginRequest):
    """获取JWT访问令牌"""
    allowed_roles = {r.value for r in Role}
    if body.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"无效角色: {body.role}")
    token = create_access_token(user_id=body.user_id, role=body.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


# ==================== 问答 ====================

@router.post("/ask", response_model=AskResponse, tags=["问答"])
async def ask_question(
    body: AskRequest,
    current_user: TokenPayload = Depends(require_permission("ask")),
):
    """提交问题并获取答案（RAG增强）"""
    agent, sid = _get_or_create_agent(body.session_id)
    try:
        result = await agent.ask(body.question)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 保存到Redis
    await redis_cache.save_conversation(sid, agent.conversation)
    _local_conversations[sid] = agent.conversation

    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result["sources"],
        has_context=result["has_context"],
        conversation_length=result["conversation_length"],
        session_id=sid,
    )


@router.post("/ask/stream", tags=["问答"])
async def ask_stream(
    body: AskRequest,
    current_user: TokenPayload = Depends(require_permission("ask")),
):
    """流式问答接口（SSE）"""
    agent, sid = _get_or_create_agent(body.session_id)

    async def event_stream():
        full = []
        async for token in agent.ask_stream(body.question):
            full.append(token)
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
        await redis_cache.save_conversation(sid, agent.conversation)
        _local_conversations[sid] = agent.conversation

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversation/{session_id}", response_model=ConversationResponse, tags=["问答"])
async def get_conversation(
    session_id: str,
    current_user: TokenPayload = Depends(require_permission("ask")),
):
    """获取指定会话的对话历史"""
    # 优先从Redis获取
    memory = await redis_cache.get_conversation(session_id)
    if memory is None:
        memory = _local_conversations.get(session_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    return ConversationResponse(
        session_id=session_id,
        messages=[
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in memory.messages
        ],
        message_count=len(memory.messages),
    )


@router.delete("/conversation/{session_id}", tags=["问答"])
async def clear_conversation(
    session_id: str,
    current_user: TokenPayload = Depends(require_permission("ask")),
):
    """清除会话"""
    await redis_cache.delete_conversation(session_id)
    _local_conversations.pop(session_id, None)
    return {"message": "会话已清除", "session_id": session_id}


# ==================== 文档管理 ====================

@router.post("/documents/upload", response_model=DocumentUploadResponse, tags=["文档"])
async def upload_document(
    file: UploadFile = File(...),
    current_user: TokenPayload = Depends(require_permission("upload")),
):
    """上传文档并自动向量化"""
    # 验证文件类型
    ext = os.path.splitext(file.filename or "")[1].lower()
    supported = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".csv"}
    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    # 保存文件
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过50MB限制")

    with open(file_path, "wb") as f:
        f.write(content)

    # 解析并向量化
    try:
        docs = DocumentLoader.load(file_path)
        chunks = processor.split(docs)
        vector_store.add_documents(chunks)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {e}")

    return DocumentUploadResponse(
        filename=file.filename,
        chunks=len(chunks),
        message=f"文档 '{file.filename}' 上传成功，已生成 {len(chunks)} 个向量块",
    )


@router.get("/documents", response_model=DocumentListResponse, tags=["文档"])
async def list_documents(
    current_user: TokenPayload = Depends(require_permission("list_docs")),
):
    """列出所有已索引的文档"""
    sources = vector_store.list_sources()
    docs = []
    for src in sources:
        docs.append(DocumentInfo(
            source=src,
            chunk_count=0,  # 简化处理
        ))
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/documents/{source_path:path}", tags=["文档"])
async def delete_document(
    source_path: str,
    current_user: TokenPayload = Depends(require_permission("delete_doc")),
):
    """从向量库中删除文档"""
    count = vector_store.delete_by_source(source_path)
    return {"message": f"已删除 {count} 个文档块", "source": source_path, "chunks": count}


# ==================== 系统 ====================

@router.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """系统健康检查"""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        redis_connected=redis_cache.is_connected,
        vector_count=vector_store.get_document_count(),
    )
