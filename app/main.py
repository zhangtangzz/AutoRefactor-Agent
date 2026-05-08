from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router, redis_cache
from app.auth.database import init_db
from app.config import settings
from app.websocket.handler import ws_router

BASE_DIR = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库并连接Redis
    await init_db()
    await redis_cache.connect()
    yield
    # 关闭时断开Redis
    await redis_cache.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="企业内部智能问答Agent - RESTful API",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/ws")

# 静态文件
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
