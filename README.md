# 🐱 FF-KB-Robot 知识库机器人

## 📋 项目概览

FF-KB-Robot 是一个专注数据报告分析问答的**智能知识库机器人**，采用 **LangGraph** 框架构建，支持文档上传、向量化存储、智能检索和 AI 驱动的问答。通过 RAG（检索增强生成）架构，能够精准回答知识库相关问题。

**核心特点**：
- ✅ **纯 CLI 模式**：专注命令行交互，轻量级部署
- ✅ **统一 API 后端**：所有请求通过 302.ai 进行，无需管理多个 API Key
- ✅ **高性能向量存储**：HNSW 向量数据库，毫秒级检索速度
- ✅ **灵活工作流**：LangGraph 构建的可控 Agent 工作流
- ✅ **完整的文档处理**：支持 PDF、Word、Excel 等多种格式
- ✅ **详细的日志系统**：完整的调试和监控信息

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| **智能问答** | 基于 RAG 的上下文感知问答，支持多轮对话 |
| **向量化存储** | 使用 HNSW 算法，支持高维向量快速检索 |
| **知识库管理** | 支持创建/删除/查询多个知识库 |
| **文档管理** | 支持上传/删除文档，自动分块处理 |
| **性能监控** | 响应时间、置信度、缓存命中率等详细指标 |
| **灵活配置** | 通过 .env 轻松定制模型、参数、日志等 |

---

## 🚀 快速开始

### 1️⃣ 环境准备

```bash
# 克隆项目
cd FF-KB-Robot

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2️⃣ 配置 API Key

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入 302.ai API Key
# 需要配置的关键项：
# - OPENAI_API_KEY=<你的302.ai API Key>
# - OPENAI_API_BASE=https://api.302.ai/v1
```

**获取 API Key 的方式**：
1. 访问 [302.ai 官网](https://www.302.ai/)
2. 注册账户并获得 API Key
3. 将 API Key 填入 .env 文件

### 3️⃣ 初始化数据库

```bash
# 初始化 SQLite 数据库和向量库
python db/scripts/init_db.py
```

### 4️⃣ 运行应用

```bash
# 启动交互模式（推荐）
python main.py

# 或指定参数启动其他模式
python main.py -i                    # 交互模式
python main.py -config               # 显示配置信息
python main.py -kb kb_001 -q "问题"  # 直接查询
python main.py -kb kb_001 -upload /path/to/doc.pdf  # 上传文档
```

---

## 📖 详细使用指南

### 🎮 交互模式命令

启动 `python main.py` 进入交互模式，可用命令：

| 命令 | 描述 | 示例 |
|------|------|------|
| `list` | 列出所有知识库 | `list` |
| `<kb_id>` | 选择或创建知识库 | `kb_001` |
| `upload` | 上传文档 | `upload` 然���输入路径 |
| `info` | 查看 Agent 和知识库信息 | `info` |
| `delete-doc` | 删除文档 | `delete-doc` 然后输入文档 ID |
| `delete-kb` | 删除知识库 | `delete-kb` 需确认 |
| `exit` | 退出程序 | `exit` |
| `<问题>` | 提问（普通模式） | `什么是 LLM？` |

### 📚 使用流程示例

#### 场景 1：创建新知识库并提问

```bash
$ python main.py

欢迎使用 FF-KB-Robot 知识库机器人
======================================================================

请输入知识库 ID（或留空创建新知识库，输入 'list' 查看所有知识库）:
# 直接回车，创建新知识库
请输入知识库名称: my_knowledge_base
请输入知识库描述（可选）: 这是我的知识库

✓ 知识库已创建: kb_<自动生成ID>

提示: 输入 'exit' 退出, 'upload' 上传文档, 'info' 显示知识库信息
      输入 'delete-doc' 删除文档, 'delete-kb' 删除当前知识库

请输入你的问题（或命令）: upload
请输入文档路径: /path/to/your/document.pdf
⏳ 正在上传文档...
✓ 文档已上传: doc_12345
  - 文件名: document.pdf
  - 分块数: 45

请输入你的问题（或命令）: 这份文档讲了什么？
⏳ 正在处理你的问题...

【答案】
========...
```

#### 场景 2：使用现有知识库查询

```bash
$ python main.py -kb kb_001 -q "你对这份文件有什么看法？"

【答案】
基于文件内容...

【相关文档】
📄 文档 1
   相关度: 0.8932
   内容: ...
```

#### 场景 3：查看系统配置

```bash
$ python main.py -config

FF-KB-Robot 配置信息
======================================================================
项目名称: FF-KB-Robot
项目版本: 0.1.0

LLM 配置:
  - 提供商: openai
  - 模型: gpt-5-nano
  - API 地址: https://api.302.ai/v1
  - 温度: 0.7
  - 最大 Tokens: 2048

Embedding 配置:
  - 提供商: openai
  - 模型: text-embedding-ada-002
  - API 地址: https://api.302.ai/v1
  - 向量维度: 1536
...
```

---

## ⚙️ 配置详解

### 环境变量配置 (.env 文件)

```ini
# 🔑 302.ai API 配置（必填）
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.302.ai/v1

# 🤖 LLM 模型配置
LLM_MODEL_NAME=gpt-5-nano          # 默认模型
LLM_TEMPERATURE=0.7                # 创意度 (0.0-1.0)
LLM_MAX_TOKENS=2048                # 最大输出长度

# 🧠 Embedding 模型配置
EMBEDDING_MODEL_NAME=text-embedding-ada-002
EMBEDDING_DIMENSION=1536           # 向量维度

# 📊 向量数据库配置
VECTOR_STORE_TYPE=hnsw             # 使用 HNSW
VECTOR_STORE_PATH=./db/vector_store

# 📄 文档处理配置
CHUNK_SIZE=1024                    # 文本分块大小
CHUNK_OVERLAP=200                  # 分块重叠

# 📝 日志配置
LOG_LEVEL=INFO                     # 日志级别
LOG_FILE=./logs/app.log            # 日志文件路径
```

### 重要配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_MODEL_NAME` | gpt-5-nano | 必须与 302.ai 支持的模型一致 |
| `EMBEDDING_DIMENSION` | 1536 | 必须与 Embedding 模型维度一致 |
| `CHUNK_SIZE` | 1024 | 越小越细致，但会增加向量数量 |
| `CHUNK_OVERLAP` | 200 | 重叠长度，防止上下文断裂 |
| `LANGGRAPH_TIMEOUT` | 60 | Agent 执行超时时间（秒） |

---

## 📁 项目结构详解

```
FF-KB-Robot/
│
├── 🎯 agent/                       # LangGraph Agent 核心
│   ├── agent_core.py              # Agent 主逻辑
│   ├── state.py                   # Agent 状态定义
│   └── nodes.py                   # 工作流节点
│
├── 🧠 models/                      # LLM 和 Embedding 管理
│   ├── llm_manager.py             # LLM 管理
│   └── embedding_manager.py       # Embedding 管理
│
├── 🔍 retrieval/                   # 文档检索和知识库
│   ├── knowledge_base_manager.py  # 知识库管理
│   ├── vector_store.py            # 向量存储
│   └── retriever.py               # 检索器
│
├── ⚙️ config/                      # 配置和数据模型
│   ├── settings.py                # 配置管理
│   └── schemas.py                 # 数据模型
│
├── 💬 prompts/                     # 提示词管理
│   ├── system_prompts.py          # 系统提示词
│   └── templates.py               # 提示词模板
│
├── 🛠️ utils/                       # 工具函数
│   ├── logger.py                  # 日志工具
│   ├── validators.py              # 验证工具
│   └── helpers.py                 # 辅助函数
│
├── 📚 data/                        # 数据存储目录
│   └── (用户文档存储)
│
├── 💾 db/                          # 数据库存储
│   ├── scripts/                   # 初始化脚本
│   ├── sql_db/                    # SQLite 数据库
│   └── vector_store/              # HNSW 向量库
│
├── 📝 logs/                        # 日志输出目录
│
├── 📄 main.py                      # ⭐ CLI 主入口程序
├── 📄 requirements.txt             # 项目依赖列表
├── 📄 .env.example                 # 环境配置示例
└── 📄 README.md                    # 本文件
```

---

## 🔐 安全建议

### 1️⃣ API 密钥管理

```bash
❌ 错误：不要在代码中硬编码 API Key
const apiKey = "sk-xxxxx";

✅ 正确：使用 .env 文件
# .env
OPENAI_API_KEY=sk-xxxxx

# Python 代码
from config.settings import settings
api_key = settings.OPENAI_API_KEY
```

### 2️⃣ 数据安全

- 定期备份 `db/` 目录中的数据库文件
- 避免在日志中记录敏感信息
- 使用强密码保护服务器

### 3️⃣ 性能优化

- 调整 `CHUNK_SIZE` 根据您的文档特性
- 使用 `LANGGRAPH_MAX_ITERATIONS` 防止无限循环
- 监控 `logs/app.log` 中的性能指标

---

## 🐛 故障排查

### 问题 1：API 连接失败

```
错误: Error communicating with OpenAI API
```

**解决方案**：
1. 检查 .env 中的 `OPENAI_API_KEY` 是否正确
2. 确认 `OPENAI_API_BASE` 为 `https://api.302.ai/v1`
3. 检查网络连接和防火墙设置

### 问题 2：向量维度不匹配

```
错误: Embedding dimension mismatch
```

**解决方案**：
1. 确认 `EMBEDDING_DIMENSION` 与模型一致（默认 1536）
2. 删除旧的向量库：`rm -rf db/vector_store`
3. 重新初始化：`python db/scripts/init_db.py`

### 问题 3：文档上传失败

```
错误: Failed to process document
```

**解决方案**：
1. 检查文件格式是否支持（PDF、DOCX、XLSX）
2. 确认文件大小不超过限制
3. 查看 `logs/app.log` 中的详细错误信息

### 问题 4：查看详细日志

```bash
# 实时查看日志
tail -f logs/app.log

# 搜索错误日志
grep ERROR logs/app.log

# Windows 查看日志
type logs\app.log
```

---

## 📚 技术栈详解

### 核心框架
- **LangGraph** (>=1.0.3)：构建 AI 工作流的框架
- **LangChain** (>=1.0.5)：LLM 应用开发工具链
- **Pydantic** (>=2.5.0)：数据验证和设置管理

### AI 模型
- **LLM**：gpt-5-nano (通过 302.ai)
- **Embedding**：text-embedding-ada-002 (通过 302.ai)

### 数据存储
- **向量数据库**：HNSW (hnswlib>=0.8.0)
- **关系数据库**：SQLite3
- **文件存储**：本地文件系统

### 文档处理
- **PDF**：PyPDF2, pdf2image
- **Word**：python-docx
- **Excel**：openpyxl

### 异步支持
- **aiofiles**：异步文件操作
- **httpx**：异步 HTTP 请求
- **asyncio**：Python 异步编程

---

## 🎓 学习资源

| 资源 | 链接 |
|------|------|
| LangGraph 文档 | https://langchain-ai.github.io/langgraph/ |
| LangChain 文档 | https://python.langchain.com/ |
| Pydantic 文档 | https://docs.pydantic.dev/ |
| HNSW 文档 | https://github.com/nmslib/hnswlib |
| 302.ai | https://www.302.ai/ |

---

## 📞 支持和反馈

如果您遇到问题或有改进建议，欢迎：
- 查看 `logs/app.log` 了解详细错误信息
- 检查本 README 的「故障排查」部分
- 提交 Issue 或 Pull Request

---

## 📜 项目信息

| 项目 | 内容 |
|------|------|
| **项目名** | FF-KB-Robot |
| **版本** | 0.1.0 |
| **模式** | CLI Only（纯命令行） |
| **LLM 模型** | gpt-5-nano |
| **Embedding 模型** | text-embedding-ada-002 |
| **向量库** | HNSW |
| **数据库** | SQLite3 |
| **框架** | LangGraph + LangChain |
| **Python 版本** | >=3.8 |

---

<div align="center">

**🌟 如果对您有帮助，请给个 Star！**

Made with 🐱 by FF-KB-Robot Team

</div>
