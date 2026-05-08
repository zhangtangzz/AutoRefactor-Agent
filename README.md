# 企业智能问答 Agent

基于 RAG 架构的企业内部智能问答系统，支持多格式文档检索、多轮对话、JWT 认证和 RBAC 权限控制。

## 功能特性

- **自然语言问答**: 基于 Claude API 的智能问答，支持 RAG 增强检索
- **多轮对话**: 支持 3-5 轮上下文记忆，可持久化到 Redis
- **文档检索**: 支持 PDF / Word / Excel / TXT / Markdown / CSV 等格式
- **向量化存储**: 使用 ChromaDB + 中文 sentence-transformer 做本地向量化
- **JWT 认证**: 基于角色的访问控制 (admin / user / viewer)
- **Redis 缓存**: 会话缓存和响应缓存
- **WebSocket**: 支持实时流式问答推送
- **RESTful API**: 完整的 API 接口，支持流式 (SSE) 输出

## 项目结构

```
enterprise-qa-agent/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置管理
│   ├── auth/
│   │   ├── jwt_handler.py    # JWT 处理
│   │   └── rbac.py           # RBAC 权限控制
│   ├── api/
│   │   ├── routes.py         # API 路由
│   │   └── schemas.py        # 数据模型
│   ├── agent/
│   │   ├── qa_agent.py       # RAG 问答 Agent
│   │   └── conversation.py   # 对话记忆
│   ├── document/
│   │   ├── loader.py         # 多格式文档加载
│   │   ├── processor.py      # 文本分块
│   │   └── vector_store.py   # 向量数据库
│   ├── cache/
│   │   └── redis_cache.py    # Redis 缓存
│   └── websocket/
│       └── handler.py        # WebSocket 处理
├── static/
│   └── index.html            # 前端页面
├── uploads/                   # 文档上传目录
├── data/chroma/               # ChromaDB 持久化数据
├── requirements.txt
├── .env.example
├── run.py                    # 启动脚本
└── README.md
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- Redis (可选，用于缓存)

### 2. 安装依赖

```bash
cd enterprise-qa-agent
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 ANTHROPIC_API_KEY
```

必填配置:
- `ANTHROPIC_API_KEY`: Claude API 密钥

可选配置:
- `CLAUDE_MODEL`: 模型选择 (默认 claude-sonnet-4-6)
- `REDIS_URL`: Redis 连接地址 (未配置则使用内存缓存)
- `CHROMA_PERSIST_DIR`: ChromaDB 数据目录

### 4. 启动服务

```bash
python run.py
```

访问 http://localhost:8000 打开前端页面。

## API 接口

### 认证

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo", "role": "user"}'
```

### 问答

```bash
# 提出问题
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "公司年假政策是什么？", "session_id": null}'

# 多轮对话（传入前一次返回的 session_id）
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "如何申请？", "session_id": "abc123"}'

# 流式问答 (SSE)
curl -X POST http://localhost:8000/api/v1/ask/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "介绍一下公司福利"}'

# 获取对话历史
curl http://localhost:8000/api/v1/conversation/abc123 \
  -H "Authorization: Bearer <token>"

# 清除会话
curl -X DELETE http://localhost:8000/api/v1/conversation/abc123 \
  -H "Authorization: Bearer <token>"
```

### 文档管理

```bash
# 上传文档
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@公司政策.pdf"

# 列出文档
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <token>"
```

### 系统

```bash
curl http://localhost:8000/api/v1/health
```

## RBAC 角色权限

| 权限        | admin | user | viewer |
|------------|-------|------|--------|
| 提问 (ask)  | ✓     | ✓    | ✓      |
| 上传文档    | ✓     | ✓    | ✗      |
| 删除文档    | ✓     | ✗    | ✗      |
| 文档列表    | ✓     | ✓    | ✓      |
| 管理用户    | ✓     | ✗    | ✗      |

## WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');
ws.send(JSON.stringify({ action: 'ask', question: '年假政策?' }));
ws.send(JSON.stringify({ action: 'clear' }));
```

## 技术栈

- **大模型**: Anthropic Claude (Sonnet 4.6)
- **框架**: FastAPI + LangChain
- **向量数据库**: ChromaDB
- **Embedding**: shibing624/text2vec-base-chinese (本地)
- **缓存**: Redis
- **文档解析**: pdfplumber / PyPDF2 / python-docx / openpyxl
