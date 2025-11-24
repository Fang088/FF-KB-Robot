"""
性能埋点和追踪工具 - 为 RAG 系统提供详细的性能指标
支持异步和同步操作，记录每一步的执行时间和状态
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, List
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """单个性能指标"""
    name: str                      # 指标名称
    start_time: float              # 开始时间
    end_time: Optional[float] = None
    duration_ms: float = 0.0       # 持续时间（毫秒）
    status: str = "running"        # 状态：running, completed, error
    message: str = ""              # 附加信息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息

    def complete(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        """标记指标为完成"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "completed"
        self.message = message
        if details:
            self.details.update(details)

    def error(self, error_msg: str):
        """标记指标为错误"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "error"
        self.message = error_msg

    def __str__(self) -> str:
        """格式化输出"""
        status_icon = {
            "running": "⏳",
            "completed": "✅",
            "error": "❌",
        }.get(self.status, "❓")

        result = f"{status_icon} {self.name}: {self.duration_ms:.2f}ms"
        if self.message:
            result += f" ({self.message})"
        return result


class PerformanceTracker:
    """
    性能追踪器 - 记录整个 Agent 查询的性能指标
    """

    def __init__(self, query_id: str):
        """
        初始化追踪器

        Args:
            query_id: 查询 ID（用于关联日志）
        """
        self.query_id = query_id
        self.start_time = time.time()
        self.metrics: List[PerformanceMetric] = []
        self._metric_stack: Dict[str, PerformanceMetric] = {}

    def record_metric(
        self,
        name: str,
        duration_ms: float,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        记录一个已知时长的指标

        Args:
            name: 指标名称
            duration_ms: 时长（毫秒）
            message: 附加消息
            details: 详细信息
        """
        metric = PerformanceMetric(
            name=name,
            start_time=time.time() - duration_ms / 1000,
            end_time=time.time(),
            duration_ms=duration_ms,
            status="completed",
            message=message,
            details=details or {},
        )
        self.metrics.append(metric)
        logger.debug(f"[{self.query_id}] {metric}")

    def start_metric(self, name: str) -> PerformanceMetric:
        """
        开始一个性能指标记录

        Args:
            name: 指标名称

        Returns:
            PerformanceMetric 对象
        """
        metric = PerformanceMetric(name=name, start_time=time.time())
        self._metric_stack[name] = metric
        logger.info(f"[{self.query_id}] ⏳ 开始: {name}")
        return metric

    def end_metric(
        self,
        name: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        结束一个性能指标记录

        Args:
            name: 指标名称
            message: 附加消息
            details: 详细信息
        """
        if name not in self._metric_stack:
            logger.warning(f"[{self.query_id}] 指标 '{name}' 未开始")
            return

        metric = self._metric_stack.pop(name)
        metric.complete(message=message, details=details)
        self.metrics.append(metric)
        logger.info(f"[{self.query_id}] {metric}")

    def error_metric(self, name: str, error_msg: str):
        """
        记录指标错误

        Args:
            name: 指标名称
            error_msg: 错误消息
        """
        if name not in self._metric_stack:
            logger.warning(f"[{self.query_id}] 指标 '{name}' 未开始")
            return

        metric = self._metric_stack.pop(name)
        metric.error(error_msg)
        self.metrics.append(metric)
        logger.error(f"[{self.query_id}] {metric}")

    @contextmanager
    def track(self, name: str):
        """
        同步上下文管理器 - 自动记录时间

        Args:
            name: 指标名称

        Usage:
            with tracker.track("embedding"):
                # 执行操作
                pass
        """
        metric = self.start_metric(name)
        try:
            yield metric
            self.end_metric(name)
        except Exception as e:
            self.error_metric(name, str(e))
            raise

    @asynccontextmanager
    async def async_track(self, name: str):
        """
        异步上下文管理器 - 自动记录时间

        Args:
            name: 指标名称

        Usage:
            async with tracker.async_track("embedding"):
                # 执行异步操作
                pass
        """
        metric = self.start_metric(name)
        try:
            yield metric
            self.end_metric(name)
        except Exception as e:
            self.error_metric(name, str(e))
            raise

    def get_total_time(self) -> float:
        """获取总耗时（毫秒）"""
        return (time.time() - self.start_time) * 1000

    def get_report(self) -> str:
        """
        获取性能报告

        Returns:
            格式化的性能报告
        """
        total_time = self.get_total_time()

        report = [
            "\n" + "="*70,
            "📊 性能追踪报告",
            "="*70,
            f"查询 ID: {self.query_id}",
            f"总耗时: {total_time:.2f}ms",
            "",
            "详细指标:",
            "-"*70,
        ]

        for metric in self.metrics:
            report.append(f"  {metric}")

        report.append("-"*70)

        # 计算各环节比例
        if self.metrics:
            report.append("耗时分布:")
            for metric in self.metrics:
                percentage = (metric.duration_ms / total_time * 100) if total_time > 0 else 0
                bar = "█" * int(percentage / 2)
                report.append(f"  {metric.name:20s} {percentage:5.1f}% {bar}")

        report.append("="*70 + "\n")

        return "\n".join(report)

    def print_report(self):
        """打印性能报告"""
        print(self.get_report())

    def get_metrics_dict(self) -> Dict[str, Any]:
        """
        获取指标字典（用于返回给客户端）

        Returns:
            指标字典
        """
        return {
            "query_id": self.query_id,
            "total_ms": self.get_total_time(),
            "metrics": [
                {
                    "name": m.name,
                    "duration_ms": m.duration_ms,
                    "status": m.status,
                    "message": m.message,
                    "details": m.details,
                }
                for m in self.metrics
            ],
        }


class StreamCallback:
    """
    流式输出回调接口
    用于实时显示 Agent 的执行进度和 LLM 的生成结果
    """

    def on_start(self, stage: str, metadata: Optional[Dict[str, Any]] = None):
        """阶段开始回调"""
        pass

    def on_complete(self, stage: str, metadata: Optional[Dict[str, Any]] = None):
        """阶段完成回调"""
        pass

    def on_stream(self, chunk: str):
        """流式数据回调"""
        pass

    def on_error(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """错误回调"""
        pass


class ConsoleStreamCallback(StreamCallback):
    """控制台输出的流式回调"""

    def on_start(self, stage: str, metadata: Optional[Dict[str, Any]] = None):
        """阶段开始时打印"""
        print(f"\n⏳ {stage}...", end="", flush=True)

    def on_complete(self, stage: str, metadata: Optional[Dict[str, Any]] = None):
        """阶段完成时打印"""
        elapsed = metadata.get("elapsed_ms", 0) if metadata else 0
        print(f" ✅ ({elapsed:.0f}ms)")

    def on_stream(self, chunk: str):
        """流式数据输出"""
        print(chunk, end="", flush=True)

    def on_error(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """错误信息输出"""
        print(f" ❌ {error}")
