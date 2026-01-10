#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 启动入口

使用 PySide6 创建的桌面应用程序
"""

import sys
import subprocess
import time
import os
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from config import AppConfig

def main():
    """主函数"""
    # 启动 Modbus 仿真服务器 (后台运行)
    print("正在启动 Modbus 仿真服务器...")
    # 使用当前 Python 解释器启动
    server_process = subprocess.Popen(
        [sys.executable, "modbus_sim_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # 等待服务器启动
    time.sleep(1.5)
    
    try:
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        app.setApplicationName(AppConfig.APP_NAME)
        app.setApplicationVersion(AppConfig.APP_VERSION)
        app.setOrganizationName(AppConfig.APP_ORGANIZATION)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        # 运行事件循环
        exit_code = app.exec()
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"程序运行出错: {e}")
        
    finally:
        # 确保退出时关闭仿真服务器
        print("正在关闭 Modbus 仿真服务器...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
