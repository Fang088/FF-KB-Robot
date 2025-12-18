# 🤖 FF-KB-Robot

> 企业级 RAG 知识库系统 | LangGraph + HNSW | CLI & Web UI 双模式

## ⚡ 核心特性

| 特性 | 说明 |
|------|------|
| **双模式部署** | CLI 交互 + Streamlit Web UI |
| **毫秒级检索** | HNSW 向量库 <100ms，支持百万+ 向量 |
| **4 层缓存** | 降低 API 成本 50-70% |
| **智能工作流** | LangGraph DAG 架构 + 条件路由 |
| **多格式支持** | PDF、DOCX、XLSX、TXT 自动分块向量化 |
| **置信度评分** | 多维度综合评分（检索+完整度+关键词） |

## 🚀 5 分钟启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env：填入 302.ai API Key

# 3. 运行应用
# CLI 模式
python main.py

# Web UI（推荐，访问 http://localhost:8501）
streamlit run web_ui/Home.py
```

## ⚙️ 必需配置

```env
# API 配置（必需）
OPENAI_API_KEY=<your_302ai_api_key>
OPENAI_API_BASE=https://api.302.ai/v1

# 核心参数（可选，有默认值）
TEXT_CHUNK_SIZE=1000              # 分块大小（推荐 800-1200）
TOP_K_RETRIEVAL=5                 # 返回文档数
HNSW_EF_SEARCH=100                # 搜索精度
CACHE_ENABLED=true                # 启用缓存
```

> 详细配置参见 `.env.example`

## 📖 使用方式

### CLI 模式
```bash
python main.py              # 交互模式
python main.py -kb kb_001 -q "问题"  # 直接查询
```

### Web UI 模式
访问 `http://localhost:8501`
- 📚 知识库管理：创建/删除知识库
- 📝 文档管理：上传/删除文档
- 💬 智能问答：对话 + 文件上传
- 📊 系统监控：性能统计 + 缓存命中率

## 🔄 工作流

```
问题 → [L1 缓存检查] → HNSW 搜索 → [L3 质量评估]
→ RAG 生成 → [多维评分] → [L2 缓存] → 答案
```

**关键指标：**
| 指标 | 性能 |
|------|------|
| 检索速度 | <100ms |
| 端到端响应 | <4s |
| 缓存命中率 | 30-70% |
| API 成本节省 | 50-70% |

## 📁 核心模块

```
FF-KB-Robot/
├── agent/          # LangGraph 工作流
├── retrieval/      # HNSW 向量库 + 文档处理
├── models/         # LLM & Embedding 服务
├── web_ui/         # Streamlit Web 界面
│   ├── pages/      # 功能页面（4 个）
│   └── services/   # 后端 API 服务
├── db/             # SQLite + 向量索引
├── main.py         # CLI 入口
└── config/         # 全局配置
```

## 🛠️ 配置调优

**提高查询质量：**
```env
TOP_K_RETRIEVAL=10                # 增加返回文档数
SIMILARITY_THRESHOLD=0.3          # 降低相似度阈值
TEXT_CHUNK_SIZE=800               # 减小分块大小
```

**优化检索速度：**
```env
HNSW_EF_SEARCH=50                 # 降低搜索精度
CACHE_ENABLED=true                # 启用缓存
```

## 🔐 安全 & 数据

- ✅ API Key 存在 `.env`，不要提交到 Git
- ✅ 定期备份 `db/` 目录
- ✅ 启用 4 层缓存降低成本和隐私风险

## ❓ 常见问题

| 问题 | 解决方案 |
|------|--------|
| **连接失败** | 检查 `.env` 中的 API Key 和网络连接 |
| **向量维度不匹配** | `rm -rf db/vector_store` 后重新初始化 |
| **查询精度低** | 增加 `TOP_K_RETRIEVAL`，调整 `TEXT_CHUNK_SIZE` |

## 📦 依赖

- **langgraph** (>=1.0)：工作流编排
- **hnswlib** (>=0.8)：向量搜索
- **streamlit** (>=1.28)：Web UI
- **openai** (>=2.0)：LLM API
- **PyPDF2, python-docx, openpyxl**：文档处理

## 📋 项目信息

**FF-KB-Robot** (Fast Fetch Knowledge Base Robot) v0.1.0
- **类型**：企业级 RAG 知识库系统
- **框架**：LangGraph + LangChain
- **支持**：PDF、DOCX、XLSX、TXT
- **Python**：>=3.8

---

<div align="center">

Made with ❤️ by FF-KB-Robot Team | Powered by LangGraph + HNSW

</div>
