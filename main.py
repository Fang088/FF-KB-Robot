"""
FF-KB-Robot 主程序入口
仅支持命令行交互模式
"""

import asyncio
import argparse
import logging
from agent.agent_core import AgentCore
from retrieval.knowledge_base_manager import KnowledgeBaseManager
from config.settings import settings
from utils.logger import setup_logger

# 设置日志
logger = setup_logger()


class KBRobotCLI:
    """
    知识库机器人命令行界面 (CLI Only)
    """

    def __init__(self):
        """初始化 CLI"""
        self.agent = AgentCore()
        self.kb_manager = KnowledgeBaseManager()
        logger.info("FF-KB-Robot CLI 已启动")

    async def interactive_mode(self):
        """
        交互模式
        用户可以创建知识库、上传文档、查询问题
        """
        logger.info("进入交互模式")
        print("\n" + "=" * 70)
        print("" * 15 + "欢迎使用 FF-KB-Robot 知识库机器人")
        print("=" * 70)
        print("当前配置:")
        print(f"  - LLM 模型: {settings.LLM_MODEL_NAME}")
        print(f"  - Embedding 模型: {settings.EMBEDDING_MODEL_NAME}")
        print(f"  - API 地址: {settings.LLM_API_BASE}")
        print("=" * 70)

        # 首先需要选择或创建知识库
        kb_id = input("\n请输入知识库 ID（或留空创建新知识库）: ").strip()

        if not kb_id:
            # 创建新知识库
            kb_name = input("请输入知识库名称: ").strip()
            if not kb_name:
                print("✗ 知识库名称不能为空")
                return

            kb_desc = input("请输入知识库描述（可选）: ").strip()
            kb_info = self.kb_manager.create_knowledge_base(
                name=kb_name,
                description=kb_desc if kb_desc else None,
            )
            kb_id = kb_info["id"]
            print(f"✓ 知识库已创建: {kb_id}")

        # 交互循环
        print("\n" + "-" * 70)
        print("提示: 输入 'exit' 退出, 'upload' 上传文档, 'info' 显示知识库信息")
        print("-" * 70)

        while True:
            print()
            question = input("请输入你的问题（或命令）: ").strip()

            if not question:
                continue

            # 处理特殊命令
            if question.lower() == "exit":
                print("\n感谢使用 FF-KB-Robot，再见！\n")
                break

            if question.lower() == "info":
                info = self.agent.get_agent_info()
                print("\n" + "-" * 70)
                print("当前 Agent 配置信息:")
                print("-" * 70)
                for key, value in info.items():
                    print(f"  {key}: {value}")
                print("-" * 70)
                continue

            if question.lower() == "upload":
                file_path = input("请输入文档路径: ").strip()
                if file_path:
                    await self.upload_document(kb_id, file_path)
                continue

            # 普通查询
            print("\n⏳ 正在处理你的问题...")

            try:
                result = await self.agent.execute_query(
                    kb_id=kb_id,
                    question=question,
                    top_k=5,
                    use_tools=False,
                )
                self._print_result(result)

            except Exception as e:
                logger.error(f"处理问题时出错: {e}")
                print(f"✗ 处理失败: {e}")

    async def upload_document(self, kb_id: str, file_path: str):
        """
        上传文档到知识库

        Args:
            kb_id: 知识库 ID
            file_path: 文档路径
        """
        try:
            print(f"\n⏳ 正在上传文档: {file_path}")
            doc_info = self.kb_manager.upload_document(kb_id, file_path)
            print(f"✓ 文档已上传: {doc_info['id']}")
            print(f"  - 文件名: {doc_info['filename']}")
            print(f"  - 分块数: {doc_info['chunk_count']}")
        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            print(f"✗ 上传失败: {e}")

    async def query_kb(self, kb_id: str, question: str):
        """
        直接查询知识库

        Args:
            kb_id: 知识库 ID
            question: 问题
        """
        try:
            print(f"\n⏳ 正在查询知识库...")
            result = await self.agent.execute_query(
                kb_id=kb_id,
                question=question,
                top_k=5,
                use_tools=False,
            )
            self._print_result(result)
        except Exception as e:
            logger.error(f"查询失败: {e}")
            print(f"✗ 查询失败: {e}")

    @staticmethod
    def _print_result(result):
        """
        打印查询结果

        Args:
            result: 查询结果字典
        """
        print("\n" + "=" * 70)
        print("答案:")
        print("-" * 70)
        answer = result.get("answer", "无答案")
        print(answer)

        # 显示相关文档
        retrieved_docs = result.get("retrieved_docs", [])
        if retrieved_docs:
            print("\n相关文档:")
            print("-" * 70)
            for i, doc in enumerate(retrieved_docs, 1):
                score = doc.get("score", 0)
                content = doc.get("content", "")[:100]
                print(f"\n  {i}. 相关度: {score:.4f}")
                print(f"     内容: {content}...")

        # 显示统计信息
        print("\n" + "-" * 70)
        confidence = result.get("confidence", 0)
        response_time = result.get("response_time_ms", 0)
        print(f"置信度: {confidence:.4f} | 耗时: {response_time:.2f}ms")
        print("=" * 70)

    def print_config(self):
        """打印当前配置信息"""
        print("\n" + "=" * 70)
        print("FF-KB-Robot 配置信息")
        print("=" * 70)
        print(f"项目名称: {settings.PROJECT_NAME}")
        print(f"项目版本: {settings.PROJECT_VERSION}")
        print(f"\nLLM 配置:")
        print(f"  - 提供商: {settings.LLM_PROVIDER}")
        print(f"  - 模型: {settings.LLM_MODEL_NAME}")
        print(f"  - API 地址: {settings.LLM_API_BASE}")
        print(f"  - 温度: {settings.LLM_TEMPERATURE}")
        print(f"  - 最大 Tokens: {settings.LLM_MAX_TOKENS}")
        print(f"\nEmbedding 配置:")
        print(f"  - 提供商: {settings.EMBEDDING_PROVIDER}")
        print(f"  - 模型: {settings.EMBEDDING_MODEL_NAME}")
        print(f"  - API 地址: {settings.EMBEDDING_API_BASE}")
        print(f"  - 向量维度: {settings.EMBEDDING_DIMENSION}")
        print(f"\n数据库配置:")
        print(f"  - 向量库类型: {settings.VECTOR_STORE_TYPE}")
        print(f"  - 向量库路径: {settings.VECTOR_STORE_PATH}")
        print(f"\nLangGraph 配置:")
        print(f"  - 最大迭代次数: {settings.LANGGRAPH_MAX_ITERATIONS}")
        print(f"  - 超时时间: {settings.LANGGRAPH_TIMEOUT}秒")
        print(f"\n日志配置:")
        print(f"  - 日志级别: {settings.LOG_LEVEL}")
        print(f"  - 日志文件: {settings.LOG_FILE}")
        print("=" * 70 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FF-KB-Robot 知识库机器人 (CLI 模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：

  # 启动交互模式（默认）
  python main.py -i
  python main.py

  # 直接查询知识库
  python main.py -kb kb_001 -q "你的问题"

  # 上传文档
  python main.py -kb kb_001 -upload /path/to/document.pdf

  # 显示配置信息
  python main.py -config

注意：
  - 所有 API 请求都通过 302.ai API (https://api.302.ai/v1) 进行
  - LLM 模型: gpt-5-nano
  - Embedding 模型: text-embedding-ada-002
  - 请在 .env 文件中配置 API Key
        """,
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="启动交互模式（默认）"
    )
    parser.add_argument(
        "-kb", "--knowledge-base",
        type=str,
        help="知识库 ID"
    )
    parser.add_argument(
        "-upload",
        type=str,
        help="上传文档（指定文件路径）"
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="查询问题"
    )
    parser.add_argument(
        "-config",
        action="store_true",
        help="显示配置信息"
    )

    args = parser.parse_args()

    try:
        cli = KBRobotCLI()

        if args.config:
            cli.print_config()
        elif args.knowledge_base and args.upload:
            asyncio.run(cli.upload_document(args.knowledge_base, args.upload))
        elif args.knowledge_base and args.query:
            asyncio.run(cli.query_kb(args.knowledge_base, args.query))
        else:
            # 默认启动交互模式
            asyncio.run(cli.interactive_mode())

    except KeyboardInterrupt:
        print("\n\n程序已中断\n")
        logger.info("程序已中断")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        print(f"\n✗ 发生错误: {e}\n")


if __name__ == "__main__":
    main()
