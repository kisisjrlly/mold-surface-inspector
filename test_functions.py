#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 功能测试脚本

用于测试各项交互功能
"""

from PySide6.QtWidgets import QApplication
from main_window import MainWindow
import sys

def test_ui_interactions():
    """测试UI交互功能"""
    app = QApplication(sys.argv)
    window = MainWindow()
    
    print("功能测试项目:")
    print("1. 加载模型按钮 - 应打开文件对话框")
    print("2. 开始测量按钮 - 应开始模拟数据生成")
    print("3. 暂停按钮 - 应暂停数据生成")
    print("4. 停止按钮 - 应停止数据生成并重置状态")
    print("5. 参数读取 - 应能读取输入框中的数值")
    print("\n界面已启动，请手动测试各项功能...")
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_ui_interactions())
