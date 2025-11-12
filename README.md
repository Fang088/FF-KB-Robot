# FF-KB-Robot 知识库机器人

## 📋 项目概览

FF-KB-Robot 是一个专注数据报告分析问答的知识库机器人，采用 LangGraph 框架构建，支持文档上传、向量化存储、智能检索和 AI 驱动的问答。

**特点**：
- 仅 CLI 模式，专注命令行交互
- 统一使用 302.ai API 作为 LLM 和 Embedding 后端
- LLM 模型：gpt-5-nano
- Embedding 模型：text-embedding-ada-002
- 基于 RAG (检索增强生成) 架构

## 🎯 核心特性

- **智能问答**：基于 RAG 的智能问答系统
- **向量存储**：集成 ChromaDB 进行向量数据存储和相似度检索
- **统一 API**：所有 API 请求通过 302.ai 进行
- **灵活工作流**：使用 LangGraph 构建可控的 Agent 工作流
- **自定义工具**：支持集成自定义工具
- **详细日志**：完整的日志系统用于调试和监控

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

```bash
# 复制环境配置
cp .env.example .env

# 编辑 .env 文件，填入 302.ai API Key
vim .env  # 或使用其他编辑器
```

### 3. 初始化数据库

```bash
python db/scripts/init_db.py
```

### 4. 运行应用

```bash
# 启动交互模式（默认）
python main.py

# 显示配置信息
python main.py -config

# 直接查询知识库
python main.py -kb kb_001 -q "你的问题"

# 上传文档
python main.py -kb kb_001 -upload /path/to/document.pdf
```

## 📖 使用指南

### 交互模式

启动交互模式后，你可以：

1. **创建知识库**：输入空白时创建新知识库
2. **提问**：直接输入问题，AI 会基于知识库内容回答
3. **上传文档**：输入 `upload` 命令上传新文档
4. **查看信息**：输入 `info` 查看 Agent 配置
5. **退出**：输入 `exit` 退出程序

## 📦 API 配置

所有 API 请求使用统一的 302.ai 配置：

```
API 地址: https://api.302.ai/v1
LLM 模型: gpt-5-nano
Embedding 模型: text-embedding-ada-002
```

## 🔧 配置说明

详见 `.env.example` 文件，主要配置项：

- **LLM 配置**：模型、API 密钥、温度等
- **Embedding 配置**：模型、维度等
- **数据库配置**：存储路径、类型等
- **文档处理**：分块大小、重叠等
- **日志配置**：日志级别、存储路径等

## 📝 注意事项

1. **API 密钥安全**：不要在代码中硬编码 API 密钥，使用 .env 文件
2. **向量维度**：确保与 Embedding 模型配置一致（默认 1536）
3. **分块策略**：可根据文档类型调整 CHUNK_SIZE 和 CHUNK_OVERLAP
4. **错误处理**：查看日志文件了解详细错误信息

## 📁 项目结构

```
FF-KB-Robot/
├── agent/                          # LangGraph Agent 核心
├── models/                         # LLM 和 Embedding 管理
├── retrieval/                      # 文档检索和知识库
├── config/                         # 配置和数据模型
├── prompts/                        # 提示词管理
├── utils/                          # 工具函数
├── data/                           # 数据存储
├── db/                             # 数据库存储
├── main.py                         # CLI 主入口
├── requirements.txt                # 项目依赖
├── .env.example                    # 环境配置示例
└── README.md                       # 项目说明
```

## 📚 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [302.ai](https://www.302.ai/)

---

**项目版本**：0.1.0  
**模式**：CLI Only  
**LLM**: gpt-5-nano | **Embedding**: text-embedding-ada-002
