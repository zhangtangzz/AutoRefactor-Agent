import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "企业智能问答Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Anthropic Claude API (支持 DeepSeek Anthropic 兼容接口)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_BASE_URL: Optional[str] = os.getenv("ANTHROPIC_BASE_URL")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    # ChromaDB (向量数据库)
    CHROMA_PERSIST_DIR: str = os.getenv(
        "CHROMA_PERSIST_DIR", "./data/chroma"
    )
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "enterprise_docs")

    # 文档分块
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # 对话记忆
    MAX_CONVERSATION_TURNS: int = int(os.getenv("MAX_CONVERSATION_TURNS", "5"))
    CONVERSATION_TTL: int = int(os.getenv("CONVERSATION_TTL", "3600"))

    # 检索
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))

    # 上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB


settings = Settings()
