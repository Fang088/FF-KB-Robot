@echo off
REM FF-KB-Robot Web UI 快速启动脚本

echo.
echo ================================================
echo   🤖 FF-KB-Robot Web UI 启动器
echo   企业级智能知识库 RAG 问答系统
echo ================================================
echo.

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python 环境
    echo 请先安装 Python 3.8+ 喵～
    pause
    exit /b 1
)

echo ✅ Python 环境检测通过
echo.

REM 检查 Streamlit
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未找到 Streamlit，正在安装...
    pip install streamlit
    echo.
)

echo ✅ Streamlit 已安装
echo.

REM 启动应用
echo 🚀 正在启动 FF-KB-Robot Web UI...
echo 📍 访问地址: http://localhost:8501
echo.
echo 💡 提示: 按 Ctrl+C 可以停止服务器喵～
echo.

streamlit run web_ui/Home.py

pause
