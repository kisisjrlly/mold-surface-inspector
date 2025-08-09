#!/bin/bash

# 模具曲面精度分析系统 - 安装脚本

echo "=========================================="
echo "模具曲面精度分析系统 - 安装脚本"
echo "=========================================="

# 检查 Python 版本
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "发现 Python: $python_version"
else
    echo "错误: 未找到 Python3，请先安装 Python 3.8 或更高版本"
    exit 1
fi

# 检查 pip
if command -v pip3 &> /dev/null; then
    echo "发现 pip3"
else
    echo "错误: 未找到 pip3，请先安装 pip"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境？(y/n) [推荐]: " create_venv
if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "虚拟环境已激活"
fi

# 升级 pip
echo "升级 pip..."
pip3 install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip3 install -r requirements.txt

if [[ $? -eq 0 ]]; then
    echo "=========================================="
    echo "安装完成！"
    echo "=========================================="
    echo ""
    echo "运行应用程序："
    echo "  python3 app.py"
    echo ""
    if [[ $create_venv =~ ^[Yy]$ ]]; then
        echo "注意：如果创建了虚拟环境，请先激活它："
        echo "  source venv/bin/activate"
        echo ""
    fi
else
    echo "安装失败，请检查错误信息"
    exit 1
fi
