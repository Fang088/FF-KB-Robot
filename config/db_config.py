"""
项目配置模块 - 集中管理所有配置，包括数据库路径

这样做的好处：
1. 所有配置在一个地方，易于维护
2. 无论从哪里启动应用，都能正确找到资源
3. 容易进行环境切换（开发、测试、生产）
"""

from pathlib import Path
import os

# ==================== 项目根目录 ====================
# 自动检测项目根目录（基于此文件所在位置）
PROJECT_ROOT = Path(__file__).parent.parent

# ==================== 数据库配置 ====================
DB_DIR = PROJECT_ROOT / "db" / "sql_db"
DB_PATH = DB_DIR / "kbrobot.db"

# 确保数据库目录存在
DB_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 日志配置 ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ==================== 验证配置 ====================
if __name__ == "__main__":
    print("项目配置验证")
    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据库目录: {DB_DIR}")
    print(f"数据库文件: {DB_PATH}")
    print(f"数据库存在: {DB_PATH.exists()}")
    print("=" * 60)
