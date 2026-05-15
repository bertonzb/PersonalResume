# DeepScribe — 个人知识库深度研究助手

基于 RAG + AI Agent 的智能知识管理平台。上传文档后，Agent 能自主调用检索、搜索、摘要等工具，完成多步深度研究任务。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + Ant Design |
| 后端 | Python 3.12 + FastAPI + Celery + Pydantic |
| AI | LangChain + OpenAI 兼容 API（DeepSeek / vLLM / SGLang 可切换） |
| 向量库 | ChromaDB |
| 数据库 | SQL Server（aioodbc 异步驱动） + Redis |
| 日志追踪 | structlog + TraceID + OpenTelemetry |

## 架构

```
┌─────────────────────────────────────────────┐
│            前端  Next.js 14                  │
│        App Router + Ant Design              │
├─────────────────────────────────────────────┤
│            API 网关  FastAPI + JWT            │
├──────────┬──────────┬──────────┬────────────┤
│  Skills  │  Agent   │  Tools   │   MCP      │
│  深度研究 │  智能编排 │  检索/搜索 │  天气/文件  │
│  知识周报 │  混合路由 │  文档摘要 │  标准协议   │
├──────────┴──────────┴──────────┴────────────┤
│        AI 模型路由  LLMProvider               │
│        (API / vLLM / SGLang)                │
├──────────────────┬──────────────────────────┤
│   向量数据库       │      业务数据库            │
│  ChromaDB        │   SQL Server + Redis      │
├──────────────────┴──────────────────────────┤
│     可观测性  structlog + OpenTelemetry       │
└─────────────────────────────────────────────┘
```

## 环境要求

| 基础设施 | 用途 | 说明 |
|----------|------|------|
| SQL Server | 用户、文档、对话数据持久化 | 需安装 ODBC Driver 17 for SQL Server |
| Redis | Celery 任务队列消息代理 | 异步任务依赖 |
| ChromaDB | 向量语义检索 | 支持本地文件持久化（无需单独服务） |
| LLM API | AI 对话与推理 | DeepSeek / OpenAI / vLLM / SGLang 任选 |

## 快速启动

### 1. 环境变量

项目根目录已有 `.env` 文件，按需修改：

```bash
# 必填
LLM_API_KEY=sk-your-key-here       # DeepSeek 或 OpenAI API Key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 数据库（默认：SQL Server 命名实例 BERTON\MYDATABASE）
DATABASE_URL=mssql+aioodbc://用户名:密码@主机:1433/数据库名?odbc_connect=...

# 可选
REDIS_URL=redis://localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

### 2. 数据库初始化

运行 SQL 建库脚本（SSMS 中执行），或启动后端自动建表：

```
backend/scripts/init_sqlserver.sql
```

### 3. 本地开发

**前端**：

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:3000
```

**后端**：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
```

## 项目结构

```
deepscribe/
├── frontend/                        # Next.js 14 前端（腾讯元宝风格）
│   ├── src/
│   │   ├── app/                     # 页面路由
│   │   │   ├── layout.tsx           # 根布局（Ant Design 中文配置）
│   │   │   ├── globals.css          # 全局样式（元宝主题：侧边栏/气泡/卡片）
│   │   │   ├── page.tsx             # 首页（Hero + 功能卡片）
│   │   │   ├── chat/page.tsx        # 对话页 + Agent 执行面板
│   │   │   ├── knowledge/page.tsx   # 知识库（文件上传 Drag & Drop）
│   │   │   ├── settings/page.tsx    # 设置页
│   │   │   └── _components/         # 页面级组件
│   │   │       └── HealthStatus.tsx  # 后端健康状态指示器
│   │   ├── components/              # 通用组件
│   │   │   ├── Sidebar.tsx          # 侧边栏导航
│   │   │   ├── chat/
│   │   │   │   ├── ChatBubble.tsx   # 消息气泡（含来源引用/重试）
│   │   │   │   └── ChatInput.tsx    # 对话输入框（Enter 发送）
│   │   │   ├── upload/
│   │   │   │   └── FileUpload.tsx   # Ant Design 拖拽上传
│   │   │   └── agent-panel/
│   │   │       ├── AgentPanel.tsx    # Agent 推理过程可视化
│   │   │       └── StepCard.tsx      # 单步卡片（工具/状态/耗时）
│   │   ├── types/                   # TypeScript 类型定义
│   │   │   ├── chat.ts              # ChatMessage / SourceItem
│   │   │   ├── agent.ts             # AgentStatus / AgentStep
│   │   │   └── index.ts             # ApiResponse<T> / HealthResponse
│   │   └── lib/
│   │       ├── api.ts               # API 请求封装（泛型 fetch + 错误处理）
│   │       └── utils.ts             # 工具函数（cn 类名合并）
│   └── ...
├── backend/                         # FastAPI 后端
│   ├── app/
│   │   ├── api/                     # 路由层
│   │   │   ├── health.py            # GET  /api/v1/health
│   │   │   ├── auth.py              # POST /api/v1/auth/register /login
│   │   │   ├── upload.py            # POST /api/v1/documents/upload
│   │   │   ├── chat.py              # POST /api/v1/chat/  |  /chat/agent
│   │   │   └── deps.py              # 依赖注入（DB session / 服务工厂）
│   │   ├── services/                # 业务逻辑层
│   │   │   ├── auth_service.py      # 注册 / 登录 / 用户查询
│   │   │   ├── document_service.py  # 文档上传 / 列表 / 详情
│   │   │   └── chat_service.py      # RAG 对话（结构化 Prompt）
│   │   ├── agent/                   # AI Agent 引擎
│   │   │   ├── orchestrator.py      # 主编排器（天气预检 → RAG 管道）
│   │   │   ├── tools/               # Agent 工具
│   │   │   │   ├── doc_retrieval.py # 知识库文档检索
│   │   │   │   ├── web_search.py    # 互联网搜索（Tavily）
│   │   │   │   └── doc_summary.py   # LLM 文档摘要
│   │   │   ├── skills/              # 复杂技能组合
│   │   │   │   ├── deep_research.py # 深度研究（检索→搜索→摘要→报告）
│   │   │   │   └── weekly_report.py # 知识库周报
│   │   │   └── mcp/                 # MCP 协议（Model Context Protocol）
│   │   │       ├── server.py        # 本地 MCP Server（文件读写 + 天气查询）
│   │   │       └── client.py        # MCP Client（工具发现 + 调用）
│   │   ├── rag/                     # RAG 检索增强生成管道
│   │   │   ├── embedding.py         # Embedding 向量化（OpenAI 兼容 API）
│   │   │   ├── vector_store.py      # ChromaDB 向量数据库封装
│   │   │   ├── retriever.py         # 混合检索（向量语义 + 关键词精确）
│   │   │   └── reranker.py          # 重排序接口（预留 BGE-Reranker）
│   │   ├── models/                  # SQLAlchemy ORM 数据模型
│   │   │   ├── base.py              # 抽象基类（id / created_at / updated_at）
│   │   │   ├── user.py              # 用户表
│   │   │   ├── document.py          # 文档表
│   │   │   ├── conversation.py      # 会话表
│   │   │   └── message.py           # 消息表
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   │   ├── auth.py              # RegisterRequest / TokenResponse
│   │   │   ├── chat.py              # ChatRequest / ChatResponse
│   │   │   └── document.py          # DocumentUploadResponse
│   │   ├── core/                    # 基础组件
│   │   │   ├── config.py            # 配置中心（18 项配置字段）
│   │   │   ├── database.py          # 异步引擎 + Session 工厂
│   │   │   ├── llm_provider.py      # LLM 工厂（api / vllm / sglang）
│   │   │   ├── security.py          # 密码哈希 + JWT + API Key 加密
│   │   │   ├── logging.py           # structlog 结构化日志
│   │   │   ├── tracing.py           # TraceID 中间件（OpenTelemetry）
│   │   │   └── exceptions.py        # 统一异常定义
│   │   └── tasks/                   # Celery 异步任务
│   │       ├── celery_app.py        # Celery 配置 + Beat 定时
│   │       └── jobs.py              # 文档入库 / 深度研究任务
│   ├── scripts/
│   │   └── init_sqlserver.sql       # SQL Server 建库建表脚本
│   └── requirements.txt
├── .env                             # 环境变量
└── README.md
```

## 核心功能

### RAG 对话（混合检索 + 结构化 Prompt）

上传 PDF/TXT/MD → 自动分块 → Embedding → ChromaDB 入库。

对话时执行**三阶段检索**：
1. **向量语义检索** — ChromaDB 余弦相似度
2. **关键词精确匹配** — BM25 风格分词命中
3. **重排序** — Reranker 接口（当前 PassThrough，可接入 BGE-Reranker）

生成时注入**结构化 Prompt**：
- 场景识别（问答 vs 操作指引）
- Few-Shot 示例
- 幻觉抑制规则（禁止编造、必须标注来源、不确定时必须明说）

### Agent 智能编排

AgentOrchestrator 支持两级路由：
- **关键词预检** — 天气类查询直接调用 MCP 工具（wttr.in），跳过 LLM
- **RAG 管道** — 其他查询走 ChatService 三阶段检索 + LLM 生成

可用工具：
- `doc_retrieval` — 知识库文档检索
- `web_search` — Tavily 互联网搜索
- `doc_summary` — LLM 文档摘要
- `mcp_filesystem` — 文件读写

### MCP 协议工具

自建本地 MCP Server，提供 3 个工具：
- `read_file` — 读取服务器文件
- `write_file` — 写入文件（含路径穿越保护）
- `query_weather` — 天气查询（wttr.in 免费 API，支持中文城市名）

### LLM 多模式切换

通过配置 `LLM_MODE` 切换推理后端：
| mode | 说明 | 配置 |
|------|------|------|
| `api` | 云端 API（DeepSeek / OpenAI） | `LLM_BASE_URL` + `LLM_API_KEY` |
| `vllm` | 本地 vLLM 推理 | `LLM_LOCAL_URL` + `LLM_LOCAL_MODEL` |
| `sglang` | 本地 SGLang 推理 | `LLM_LOCAL_URL` + `LLM_LOCAL_MODEL` |

### 前端元宝风格 UI

- 侧边栏导航（260px，SVG 图标，四页面路由）
- 聊天气泡（用户蓝色右对齐 / AI 白色左对齐 + 来源引用）
- Agent 执行面板（右侧 300px，实时展示工具调用步骤）
- 拖拽上传（Ant Design Dragger，PDF/TXT/MD 20MB 限制）
- 健康状态指示器（绿色上线 / 红色离线）

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/documents/upload` | 文档上传（PDF/TXT/MD） |
| POST | `/api/v1/chat/` | RAG 对话 |
| POST | `/api/v1/chat/agent` | Agent 对话（含工具调用步骤） |

## License

MIT
