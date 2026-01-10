#!/bin/bash
# 模具曲面精度分析系统启动脚本

echo "===================================="
echo "模具曲面精度分析系统启动中..."
echo "===================================="

# 检查conda环境
if ! conda info --envs | grep -q "inspector"; then
    echo "❌ 错误: 找不到 inspector conda环境"
    echo "请先运行: conda create -n inspector python=3.9"
    echo "然后安装依赖: conda activate inspector && pip install -r requirements.txt"
    exit 1
fi

# 激活conda环境
echo "🔄 激活 conda 环境..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate inspector

# 检查关键依赖
echo "🔍 检查依赖包..."
if ! python -c "import PySide6; import pandas; import numpy; import matplotlib" 2>/dev/null; then
    echo "❌ 错误: 缺少必要的依赖包"
    echo "请运行: pip install -r requirements.txt"
    exit 1
fi

# 启动应用程序
echo "🚀 启动应用程序..."
python app.py

echo "✅ 应用程序已退出"
