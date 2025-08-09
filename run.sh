#!/bin/bash

# 模具曲面精度分析系统 - 运行脚本
# 专为 conda pyside-env 环境设计

echo "=========================================="
echo "模具曲面精度分析系统"
echo "=========================================="

# 激活 conda 环境
echo "激活 pyside-env 环境..."
source activate pyside-env

# 检查是否成功激活
if [[ "$CONDA_DEFAULT_ENV" == "pyside-env" ]]; then
    echo "环境激活成功: $CONDA_DEFAULT_ENV"
else
    echo "警告: 环境可能未正确激活"
fi

# 运行应用程序
echo "启动应用程序..."
python app.py
