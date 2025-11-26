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
        print("=" * 70)

        # 首先需要选择或创建知识库 - 循环直到选择有效
        kb_id = None
        while kb_id is None:
            input_kb_id = input("\n请输入知识库 ID（或留空创建新知识库，输入 'list' 查看所有知识库）: ").strip()

            if input_kb_id.lower() == "list":
                # 显示所有知识库
                kbs = self.kb_manager.get_all_kbs()
                if not kbs:
                    print("\n✗ 没有找到任何知识库")
                else:
                    print("\n" + "-" * 70)
                    print("所有知识库:")
                    print("-" * 70)
                    for i, kb in enumerate(kbs, 1):
                        print(f"\n  {i}. ID: {kb['id']}")
                        print(f"     名称: {kb['name']}")
                        print(f"     文档数: {kb['document_count']}")
                        print(f"     分块数: {kb['total_chunks']}")
                        print(f"     创建时间: {kb['created_at']}")
                        if kb['description']:
                            print(f"     描述: {kb['description']}")
                    print("-" * 70)
                continue  # 继续循环获取输入
            
            if input_kb_id.lower() == "config":
                self.print_config()
                continue

            if not input_kb_id:
                # 创建新知识库
                kb_name = input("请输入知识库名称: ").strip()
                if not kb_name:
                    print("✗ 知识库名称不能为空，请重新输入")
                    continue

                kb_desc = input("请输入知识库描述（可选）: ").strip()
                try:
                    kb_info = self.kb_manager.create_knowledge_base(
                        name=kb_name,
                        description=kb_desc if kb_desc else None,
                    )
                    kb_id = kb_info["id"]
                    print(f"✓ 知识库已创建: {kb_id}")
                except Exception as e:
                    print(f"✗ 创建知识库失败: {e}")
                    continue
            else:
                # 检查知识库 ID 是否存在
                if self.kb_manager.check_kb_exists(input_kb_id):
                    kb_id = input_kb_id
                    print(f"✓ 已选择知识库: {kb_id}")
                else:
                    print(f"✗ 知识库 ID '{input_kb_id}' 不存在，请重新输入或创建新的知识库")

        # 交互循环
        print("\n" + "-" * 70)
        print("提示: 输入 'exit' 退出, 'upload' 上传文档, 'info' 显示知识库信息")
        print("      输入 'delete-doc' 删除文档, 'delete-kb' 删除当前知识库")
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
                # 显示当前知识库信息
                info = self.agent.get_agent_info()
                print("\n" + "-" * 70)
                print("当前 Agent 配置信息:")
                print("-" * 70)
                for key, value in info.items():
                    print(f"  {key}: {value}")
                print("-" * 70)

                # 显示当前知识库的详细信息
                kbs = self.kb_manager.get_all_kbs()
                kb_info = next((kb for kb in kbs if kb['id'] == kb_id), None)
                if kb_info:
                    print("\n" + "-" * 70)
                    print("当前知识库信息:")
                    print("-" * 70)
                    print(f"  ID: {kb_info['id']}")
                    print(f"  名称: {kb_info['name']}")
                    print(f"  文档数: {kb_info['document_count']}")
                    print(f"  分块数: {kb_info['total_chunks']}")
                    print(f"  创建时间: {kb_info['created_at']}")
                    print(f"  更新时间: {kb_info['updated_at']}")
                    if kb_info['description']:
                        print(f"  描述: {kb_info['description']}")
                    if kb_info['tags']:
                        print(f"  标签: {', '.join(kb_info['tags'])}")
                    print("-" * 70)

                    # 显示当前知识库的文档列表
                    documents = self.kb_manager.get_kb_documents(kb_id)
                    if documents:
                        print("\n" + "-" * 70)
                        print("知识库中文档:")
                        print("-" * 70)
                        for i, doc in enumerate(documents, 1):
                            print(f"\n  {i}. 文件名: {doc['filename']}")
                            print(f"     ID: {doc['id']}")
                            print(f"     分块数: {doc['chunk_count']}")
                            print(f"     上传时间: {doc['created_at']}")
                        print("-" * 70)
                continue

            if question.lower() == "upload":
                file_path = input("请输入文档路径: ").strip()
                if file_path:
                    await self.upload_document(kb_id, file_path)
                continue

            if question.lower() == "delete-doc":
                doc_id = input("请输入要删除的文档 ID: ").strip()
                if doc_id:
                    await self.delete_document(doc_id)
                continue

            if question.lower() == "delete-kb":
                confirm = input(f"确定要删除知识库 '{kb_id}' 吗？此操作不可恢复！(y/N): ").strip().lower()
                if confirm == 'y':
                    await self.delete_knowledge_base(kb_id)
                    # 删除后退出当前循环
                    print("\n知识库已删除，程序将退出...")
                    return
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

    async def delete_knowledge_base(self, kb_id: str):
        """
        删除知识库

        Args:
            kb_id: 知识库 ID
        """
        try:
            print(f"\n⏳ 正在删除知识库: {kb_id}")
            if self.kb_manager.delete_knowledge_base(kb_id):
                print(f"✓ 知识库已删除: {kb_id}")
            else:
                print(f"✗ 删除知识库失败: 知识库不存在或已被删除")
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            print(f"✗ 删除失败: {e}")

    async def delete_document(self, doc_id: str):
        """
        删除文档

        Args:
            doc_id: 文档 ID
        """
        try:
            print(f"\n⏳ 正在删除文档: {doc_id}")
            if self.kb_manager.delete_document(doc_id):
                print(f"✓ 文档已删除: {doc_id}")
            else:
                print(f"✗ 删除文档失败: 文档不存在或已被删除")
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            print(f"✗ 删除失败: {e}")

    async def query_kb(self, kb_id: str, question: str):
        """
        直接查询知识库（支持流式显示）

        Args:
            kb_id: 知识库 ID
            question: 问题
        """
        try:
            result = await self.agent.execute_query(
                kb_id=kb_id,
                question=question,
                top_k=5,
                use_tools=False,
            )
            self._print_result(result)

        except Exception as e:
            logger.error(f"查询失败: {e}")
            print(f"❌ 查询失败: {e}")

    @staticmethod
    def _print_result(result):
        """
        打印查询结果（包含性能信息）

        Args:
            result: 查询结果字典
        """
        print("\n" + "="*70)
        print("【答案】")
        print("-"*70)
        answer = result.get("answer", "无答案")
        print(answer)

        # 显示相关文档
        retrieved_docs = result.get("retrieved_docs", [])
        if retrieved_docs:
            print("\n【相关文档】")
            print("-"*70)
            for i, doc in enumerate(retrieved_docs, 1):
                score = doc.get("score", 0)
                content = doc.get("content", "")[:10]
                print(f"\n  📄 文档 {i}")
                print(f"     相关度: {score:.4f}")
                print(f"     内容: {content}...")

        # 显示统计信息
        print("\n【统计信息】")
        print("-"*70)

        confidence = result.get("confidence", 0)
        response_time = result.get("response_time_ms", 0)
        from_cache = result.get("from_cache", False)

        confidence_level = "低 🔴" if confidence < 0.5 else "中 🟡" if confidence < 0.75 else "高 🟢"
        cache_status = "✅ 缓存命中" if from_cache else "❌ 新鲜查询"

        print(f"  置信度: {confidence:.2f} ({confidence_level})")
        print(f"  状态: {cache_status}")
        print(f"  耗时: {response_time:.0f}ms")

        # 显示置信度分解（如果有）
        metadata = result.get("metadata", {})
        breakdown = metadata.get("confidence_breakdown", {})
        if breakdown:
            print("\n  置信度分解:")
            print(f"    • 检索质量: {breakdown.get('retrieval', 0):.2f}")
            print(f"    • 答案完整度: {breakdown.get('completeness', 0):.2f}")
            print(f"    • 关键词匹配: {breakdown.get('keyword_match', 0):.2f}")
            print(f"    • 答案质量: {breakdown.get('answer_quality', 0):.2f}")
            print(f"    • 答案一致性: {breakdown.get('consistency', 0):.2f}")

        print("="*70 + "\n")

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

    try:
        cli = KBRobotCLI()
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