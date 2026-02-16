#!/bin/bash

# ClawQuant Streamlit 可视化启动脚本

echo "=========================================="
echo "  ClawQuant Streamlit 可视化平台"
echo "=========================================="
echo ""

# 检查依赖
echo "检查依赖..."
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 未安装 streamlit，正在安装依赖..."
    pip install streamlit streamlit-echarts pyecharts
fi

echo "✅ 依赖检查完成"
echo ""

# 启动应用
echo "🚀 启动 Streamlit 应用..."
echo "访问地址: http://localhost:8501"
echo ""

streamlit run web/streamlit_app.py
