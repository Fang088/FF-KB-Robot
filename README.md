# 🤖 FF-KB-Robot 知识库问答系统

**生产级 RAG 知识库系统，提供高性能智能问答和文档分析能力。**

## 📋 项目概览

FF-KB-Robot 是一个**企业级智能知识库问答系统**，基于 **LangGraph** 工作流框架和 **HNSW** 向量数据库，通过 RAG 架构精准回答文档相关问题。

### 🌟 核心特点

- 🚀 **纯 CLI 轻量级**：无需 Web 框架，快速部署
- 🔑 **统一 API 管理**：所有请求通过 302.ai（OpenAI 兼容）
- ⚡ **毫秒级检索**：HNSW 向量数据库实现 <100ms 搜索
- 🧠 **智能工作流**：LangGraph DAG 架构，支持条件路由和多步决策
- 📄 **完整文档支持**：PDF、DOCX、XLSX、TXT 自动分块向量化
- 💾 **4 层缓存系统**：Embedding、查询结果、分类、语义缓存，降低 API 成本 50-70%
- 🎯 **多维度置信度评分**：综合评估答案质量
- 📊 **性能追踪**：完整的埋点监控，实时性能指标

---

## ⚡ 工作流详解

### 问答执行流程

```
1. 检索阶段
   ├─ [L1 缓存] Embedding 缓存检查
   ├─ HNSW 向量搜索 (<100ms)
   └─ 结果过滤 → 去重 → 重排

2. 决策阶段
   ├─ [L3 缓存] 问题分类缓存检查
   ├─ 评估检索质量
   └─ 条件路由：高质量 → 生成答案 | 低质量 → 重新检索

3. 生成阶段
   ├─ RAG 提示词工程
   ├─ LLM 调用生成答案
   └─ [性能埋点] 记录耗时

4. 评估和缓存
   ├─ 多维度置信度评分（检索质量 45% + 完整度 25% + 关键词 15% + 其他 15%）
   ├─ [L2 缓存] 查询结果缓存
   └─ 返回答案 + 相关文档 + 指标
```

### 缓存系统（4层）

| 层级 | 缓存类型 | TTL | 效果 |
|-----|--------|-----|------|
| **L1** | Embedding 缓存 | 24h | 减少 Embedding API 调用 |
| **L2** | 查询结果缓存 | - | 缓存完整问答结果 |
| **L3** | 问题分类缓存 | 7d | 避免重复分类 |
| **L4** | 语义化缓存 | - | 相似问题复用答案 |

**效果**：高频查询场景下，API 成本降低 50-70%。

### 数据库架构

```
SQLite 关系数据库           HNSW 向量数据库
├─ knowledge_bases         ├─ hnsw.bin（索引）
├─ documents               ├─ metadata.json
└─ text_chunks             └─ id_mapping.json
```

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
# API 配置（必填）
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.302.ai/v1

# LLM 配置
LLM_MODEL_NAME=gpt-5-nano
LLM_TEMPERATURE=0.7                    # 0.0-1.0，越高越创意
LLM_MAX_TOKENS=2000

# Embedding 配置
EMBEDDING_MODEL_NAME=text-embedding-ada-002
EMBEDDING_DIMENSION=1536

# 向量库配置
HNSW_EF_CONSTRUCTION=200               # 构建精度
HNSW_EF_SEARCH=100                     # 搜索精度
HNSW_MAX_ELEMENTS=1000000

# 文档处理
TEXT_CHUNK_SIZE=1000                   # 推荐 800-1200
TEXT_CHUNK_OVERLAP=200

# 置信度权重
CONFIDENCE_W_RETRIEVAL=0.45
CONFIDENCE_W_COMPLETENESS=0.25
CONFIDENCE_W_KEYWORD_MATCH=0.15

# 执行配置
LANGGRAPH_TIMEOUT=60
LANGGRAPH_MAX_ITERATIONS=10

# 缓存配置
CACHE_ENABLED=true
EMBEDDING_CACHE_TTL=86400              # 24小时
CLASSIFICATION_CACHE_TTL=604800        # 7天

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# 检索配置
TOP_K=5
RETRIEVAL_SCORE_THRESHOLD=0.3
```

### 核心配置说明

| 配置项 | 说明 | 建议 |
|--------|------|------|
| **TEXT_CHUNK_SIZE** | 文本分块大小 | 800-1200 字，平衡精度和速度 |
| **HNSW_EF_SEARCH** | 向量搜索精度 | <10k向量：50 \| 10k-100k：100 \| >100k：200 |
| **TOP_K** | 返回相关文档数 | 通常 5-10 |
| **CONFIDENCE_W_RETRIEVAL** | 检索质量权重 | 0.45（较高优先级） |

---

## 📁 项目架构

### 目录结构

```
FF-KB-Robot/
├── agent/                    # LangGraph 工作流：Agent 编排、状态管理、节点执行
├── models/                   # LLM 和 Embedding 服务：调用、缓存、多供应商支持
├── retrieval/                # 文档检索核心：向量库、文档处理、知识库管理
├── config/                   # 配置和数据模型：Pydantic 设置、业务模式
├── rag/                      # RAG 优化：提示词工程、问题分类、置信度评分
├── utils/                    # 通用工具：缓存、日志、性能追踪、装饰器
├── db/                       # 数据库层：SQLite、HNSW 向量库
├── data/                     # 数据存储：临时文件、处理结果
├── logs/                     # 日志输出
├── main.py                   # ⭐ CLI 主入口（交互模式）
├── requirements.txt          # 依赖列表
├── .env.example              # 环境配置示例
└── README.md                 # 项目文档
```

### 模块说明

| 模块 | 职责 | 核心类 |
|-----|------|--------|
| **agent** | LangGraph 工作流编排 | `AgentCore`, `AgentGraph` |
| **models** | LLM 和 Embedding 服务 | `LLMService`, `EmbeddingService` |
| **retrieval** | 文档检索和知识库 | `KnowledgeBaseManager`, `HNSWVectorStore` |
| **rag** | RAG 管道优化 | `RAGOptimizer` |
| **utils** | 通用工具 | `CacheManager`, `PerformanceTracker` |

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

---

## 💡 最佳实践

### 性能优化建议

| 场景 | 优化策略 | 效果 |
|------|--------|------|
| **细粒度查询** | CHUNK_SIZE 500-800 | 精准度高，但向量数量多 |
| **通用场景** | CHUNK_SIZE 1000-1200（推荐） | 性能和精度平衡 |
| **文档摘要** | CHUNK_SIZE 1500-2000 | 向量少、成本低 |
| **高频查询** | 启用所有 4 层缓存 | API 成本 -50-70% |
| **大数据集** | HNSW_EF_SEARCH=200 | 优先精确度 |

### 常见问题排查

**连接失败**
- 验证 `.env` 中的 API Key
- 确认 API Base: `https://api.302.ai/v1`
- 检查网络连接

**向量维度不匹配**
```bash
# 更新 EMBEDDING_DIMENSION，删除旧向量库，重新初始化
rm -rf db/vector_store
python -c "from db.db_manager import init_db; init_db()"
```

**查询结果质量差**
```ini
# 调整参数
TOP_K=10
RETRIEVAL_SCORE_THRESHOLD=0.2
TEXT_CHUNK_SIZE=800
```

**查看性能指标**
```bash
tail -f logs/app.log | grep "duration\|latency\|cache"
```

---

## 📊 技术栈

| 组件 | 技术 | 说明 |
|-----|-----|------|
| **工作流框架** | LangGraph | DAG 架构，支持条件路由、循环控制 |
| **向量数据库** | HNSW | 毫秒级搜索，支持 100万+ 向量 |
| **关系数据库** | SQLite3 | 轻量级，无需独立服务 |
| **LLM & Embedding** | OpenAI SDK | 通过 302.ai（OpenAI 兼容） |
| **文档处理** | PyPDF2, python-docx, openpyxl | PDF、DOCX、XLSX 支持 |
| **异步执行** | asyncio | 并发查询支持 |

### 核心性能

| 指标 | 值 |
|-----|-----|
| **检索速度** | <100ms |
| **生成速度** | <3s |
| **总响应时间** | <4s |
| **缓存命中率** | 30-70% |
| **API 成本降低** | 50-70% |

---

## 📜 项目信息

- **项目名称**：FF-KB-Robot (Fast Fetch Knowledge Base Robot)
- **版本**：0.1.0
- **类型**：企业级 RAG 知识库系统
- **部署模式**：CLI Only（纯命令行）
- **AI 框架**：LangGraph + LangChain
- **支持格式**：PDF、DOCX、XLSX、TXT
- **Python 版本**：>=3.8

---

<div align="center">

## 🚀 快速开始

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env，填入 API Key

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python db/scripts/init_db.py

# 4. 运行应用
python main.py          # 交互模式（推荐）
python main.py -config  # 查看配置
python main.py -kb kb_001 -q "问题"  # 直接查询
```

---

**🌟 如果对您有帮助，请给个 Star！**

**💬 有问题或建议**？查看 `logs/app.log` 或提交 Issue

Made with ❤️ by FF-KB-Robot Team | Powered by LangGraph + HNSW

</div>
