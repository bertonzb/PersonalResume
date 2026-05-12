# DeepScribe — 个人知识库深度研究助手

基于 RAG + AI Agent 的智能知识管理平台。上传文档后，Agent 能自主调用检索、搜索、摘要等工具，完成多步深度研究任务。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + Ant Design |
| 后端 | Python FastAPI + Celery + Pydantic |
| AI | LangChain + OpenAI API（兼容本地模型切换） |
| 向量库 | ChromaDB（可切换 Milvus） |
| 数据库 | PostgreSQL + Redis |
| 日志追踪 | structlog + TraceID + OpenTelemetry |
| 部署 | Docker Compose 一键启动 |

## 架构

```
┌─────────────────────────────────────────────┐
│            前端  Next.js 14                  │
│        App Router + Ant Design              │
├─────────────────────────────────────────────┤
│            API 网关  FastAPI + JWT            │
├──────────┬──────────┬──────────┬────────────┤
│  Skills  │  Agent   │  Tools   │   MCP      │
│  技能组合 │  智能编排 │  工具插件 │  标准协议   │
├──────────┴──────────┴──────────┴────────────┤
│        AI 模型路由  LangChain                │
├──────────────────┬──────────────────────────┤
│   向量数据库       │      业务数据库            │
│  ChromaDB        │   PostgreSQL + Redis      │
├──────────────────┴──────────────────────────┤
│     可观测性  structlog + OpenTelemetry       │
└─────────────────────────────────────────────┘
```

## 快速启动

### 1. 环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 2. Docker Compose（推荐）

```bash
docker compose up -d
# 前端: http://localhost:3000
# 后端: http://localhost:8000/docs
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
├── frontend/                    # Next.js 14 前端
│   ├── src/
│   │   ├── app/                 # 页面路由
│   │   │   ├── page.tsx         # 首页
│   │   │   ├── chat/            # 对话页 + Agent 面板
│   │   │   ├── knowledge/       # 知识库管理
│   │   │   └── settings/        # 设置
│   │   ├── components/          # 通用组件
│   │   │   ├── ui/              # 基础 UI 封装
│   │   │   ├── chat/            # 对话组件
│   │   │   ├── upload/          # 文件上传
│   │   │   └── agent-panel/     # Agent 执行可视化
│   │   ├── lib/                 # API 客户端 & 工具
│   │   ├── types/               # TypeScript 类型
│   │   └── constants/           # 常量
│   └── ...
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # 路由层
│   │   ├── services/            # 业务逻辑
│   │   ├── agent/               # Agent 编排
│   │   │   ├── orchestrator.py  # 主编排器
│   │   │   ├── tools/           # 文档检索、搜索、摘要
│   │   │   ├── skills/          # 深度研究、知识周报
│   │   │   └── mcp/             # MCP Server/Client
│   │   ├── rag/                 # RAG 管道
│   │   ├── tasks/               # Celery 异步任务
│   │   └── core/                # 日志、安全、追踪
│   └── ...
├── mcp-server/                  # 独立 MCP Server
├── docker-compose.yml           # 一键编排
├── docs/                        # 文档
│   ├── project-plan.md          # 项目计划书
│   ├── implementation-plan.md   # 实施计划
│   ├── frontend-style-guide.md  # 前端规范
│   └── backend-style-guide.md   # 后端规范
└── README.md
```

## 核心功能

### RAG 对话
上传 PDF/TXT/MD 文档 → 自动分块 → Embedding 向量化 → 基于知识库的智能问答

### Agent 工具调用
Agent 自动选择工具完成多步任务：
- `doc_retrieval` — 知识库文档检索
- `web_search` — 互联网搜索
- `doc_summary` — 文档摘要生成

### 深度研究 Skill
拆解研究问题 → 多源并行搜索 → 对比整合 → 输出结构化提纲

### Agent 执行可视化
前端实时展示 Agent 推理过程：每一步调用了什么工具、输入输出是什么、耗时多少

### MCP 协议接入
自建 MCP Server，Agent 通过标准 MCP 协议调用文件系统工具

### 定时周报
Celery Beat 定时触发，自动生成知识库周报

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 接口文档。

主要端点：
- `GET  /api/v1/health` — 健康检查
- `POST /api/v1/auth/register` — 注册
- `POST /api/v1/auth/login` — 登录
- `POST /api/v1/documents/upload` — 上传文档
- `POST /api/v1/chat/` — RAG 对话
- `POST /api/v1/chat/agent` — Agent 对话

## License

MIT
