from typing import List, Optional

from pydantic import BaseModel, Field


# --- 认证 ---
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str = ""
    role: str = ""


# --- 问答 ---
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000, description="问题内容")
    session_id: Optional[str] = Field(default=None, description="会话ID，用于多轮对话")
    top_k: Optional[int] = Field(default=None, ge=1, le=20, description="检索数量")


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[str] = Field(default_factory=list)
    has_context: bool = False
    conversation_length: int = 0
    session_id: Optional[str] = None


class ConversationResponse(BaseModel):
    session_id: str
    messages: List[dict]
    message_count: int


# --- 文档 ---
class DocumentUploadResponse(BaseModel):
    filename: str
    chunks: int
    message: str


class DocumentInfo(BaseModel):
    source: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


# --- 管理员：用户管理 ---
class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    created_at: str


class UserListResponse(BaseModel):
    users: List[UserInfo]
    total: int


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="user")


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|user|viewer)$")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=1, max_length=128)


# --- 管理员：统计 ---
class AdminStatsResponse(BaseModel):
    user_count: int = 0
    document_count: int = 0
    vector_chunk_count: int = 0
    redis_connected: bool = False


# --- 通用 ---
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    redis_connected: bool = False
    vector_count: int = 0
