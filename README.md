# 🤖 FF-KB-Robot

> 企业级 RAG 知识库系统 | 基于 LangGraph + HNSW | CLI + Web UI 双模式部署

## ✨ 核心特点

- **🚀 双模式部署**：CLI 交互模式 + Streamlit Web UI，灵活选择
- **⚡ 毫秒级检索**：HNSW 向量数据库 <100ms 搜索，支持 100万+ 向量
- **💾 4 层缓存系统**：智能缓存策略降低 API 成本 50-70%
  - L1：Embedding 缓存（24h）
  - L2：查询结果缓存
  - L3：问题分类缓存（7d）
  - L4：语义化缓存
- **🧠 智能工作流**：LangGraph DAG 架构，条件路由 + 多步决策
- **📄 文档全支持**：PDF、DOCX、XLSX、TXT 自动分块向量化
- **🎯 多维度置信度**：综合检索质量、完整度、关键词匹配三个维度评分

## 🚀 快速开始（4 步）

### 1. 环境准备
```bash
cd FF-KB-Robot
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 API Key
```bash
cp .env.example .env
# 编辑 .env，填入 302.ai API Key
# OPENAI_API_KEY=<your_api_key>
# OPENAI_API_BASE=https://api.302.ai/v1
```

### 3. 初始化数据库
```bash
python db/scripts/init_db.py
```

### 4. 运行应用
```bash
# CLI 交互模式
python main.py

# 或 Web UI（推荐）
streamlit run web_ui/Home.py

# 或直接查询
python main.py -kb kb_001 -q "你的问题"
```

## 📖 使用指南

### CLI 模式（main.py）

| 命令 | 功能 |
|------|------|
| `list` | 列出所有知识库 |
| `<kb_id>` | 选择或创建知识库 |
| `upload` | 上传文档 |
| `info` | 查看知识库信息 |
| `delete-doc` | 删除文档 |
| `exit` | 退出 |

### Web UI 模式（Streamlit）

访问 `http://localhost:8501` 获得友好的图形界面：
- 📚 知识库管理
- 📝 文档上传和管理
- 💬 实时智能问答
- 📊 性能监控和统计

## ⚙️ 核心配置参数

| 参数 | 建议值 | 说明 |
|------|------|------|
| **TEXT_CHUNK_SIZE** | 1000 | 文本分块大小（800-1200） |
| **HNSW_EF_SEARCH** | 100 | 向量搜索精度（平衡性能和准确度） |
| **TOP_K** | 5 | 返回相关文档数 |
| **CONFIDENCE_W_RETRIEVAL** | 0.45 | 检索质量权重 |
| **EMBEDDING_CACHE_TTL** | 86400 | Embedding 缓存时长（24小时） |
| **LANGGRAPH_TIMEOUT** | 60 | 执行超时（秒） |
| **CACHE_ENABLED** | true | 启用 4 层缓存 |

> 更多参数详见 `.env.example` 文件

## 🔄 工作流架构

```
问题输入
  ↓
[L1 缓存] Embedding 缓存检查
  ↓
HNSW 向量搜索 (<100ms)
  ↓
[L3 缓存] 问题分类检查 + 检索质量评估
  ↓
├─ 高质量 → RAG 生成答案
└─ 低质量 → 重新检索
  ↓
多维度置信度评分（45% 检索 + 25% 完整度 + 15% 关键词 + 15% 其他）
  ↓
[L2 缓存] 缓存查询结果
  ↓
返回：答案 + 相关文档 + 性能指标
```

## 📊 技术栈

| 组件 | 技术 | 说明 |
|-----|------|------|
| **工作流框架** | LangGraph | DAG 架构，条件路由和循环控制 |
| **向量数据库** | HNSW | 毫秒级搜索，1000万+ 向量支持 |
| **关系数据库** | SQLite3 | 轻量级，无需独立服务 |
| **LLM & Embedding** | OpenAI SDK | 通过 302.ai（OpenAI 兼容） |
| **文档处理** | PyPDF2, python-docx, openpyxl | 多格式支持 |
| **Web 框架** | Streamlit | 快速 Web UI 开发 |

## 📁 项目结构

```
FF-KB-Robot/
├── agent/              # LangGraph 工作流编排
├── models/             # LLM 和 Embedding 服务
├── retrieval/          # 文档检索核心（HNSW 向量库）
├── rag/                # RAG 优化（提示词、评分）
├── utils/              # 缓存、日志、性能追踪
├── db/                 # SQLite + HNSW 向量库
├── web_ui/             # Streamlit Web 界面
│   ├── Home.py         # 主页
│   ├── pages/          # 功能页面
│   └── services/       # API 服务层
├── main.py             # CLI 入口
├── requirements.txt    # 依赖列表
└── .env.example        # 配置示例
```

## ⚡ 性能指标

| 指标 | 实际值 |
|------|--------|
| 检索速度 | <100ms |
| 生成速度 | <3s |
| 总响应时间 | <4s |
| 缓存命中率 | 30-70% |
| API 成本降低 | 50-70% |

## 🔐 安全建议

1. **API Key 管理**
   - 使用 `.env` 文件，不要硬编码 API Key
   - 定期轮换 API Key

2. **数据安全**
   - 定期备份 `db/` 目录
   - 避免在日志中记录敏感信息

3. **性能优化**
   - 根据文档特性调整 `TEXT_CHUNK_SIZE`
   - 启用所有 4 层缓存降低成本

## 🐛 常见问题

**Q：连接失败怎么办？**
```bash
# 验证 .env 中的 API Key 和 API Base 地址
# 检查网络连接
```

**Q：如何提高查询质量？**
```ini
# 调整以下参数
TOP_K=10                           # 增加返回文档数
RETRIEVAL_SCORE_THRESHOLD=0.2      # 降低相似度阈值
TEXT_CHUNK_SIZE=800                # 减小分块大小
```

**Q：向量维度不匹配？**
```bash
# 删除旧向量库，重新初始化
rm -rf db/vector_store
python db/scripts/init_db.py
```

## 📦 依赖说明

- **langgraph** (>=1.0)：工作流编排框架
- **langchain** (>=1.0)：大模型应用框架
- **hnswlib** (>=0.8)：高性能向量搜索库
- **streamlit** (>=1.28)：Web UI 框架
- **openai** (>=2.0)：LLM API 客户端

## 📋 项目信息

| 项 | 值 |
|----|-----|
| 项目名称 | FF-KB-Robot (Fast Fetch Knowledge Base Robot) |
| 版本 | 0.1.0 |
| 类型 | 企业级 RAG 知识库系统 |
| 框架 | LangGraph + LangChain |
| 支持格式 | PDF、DOCX、XLSX、TXT |
| Python 版本 | >=3.8 |

---

<div align="center">

**🌟 如果对您有帮助，请给个 Star！**

Made with ❤️ by FF-KB-Robot Team | Powered by LangGraph + HNSW

</div>
