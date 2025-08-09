#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 样式管理模块

管理应用程序的 QSS 样式表
"""

class StyleManager:
    """样式管理器"""
    
    @staticmethod
    def get_main_stylesheet():
        """获取主要样式表"""
        return """
        /* ===========================================
           主窗口和基础组件样式
        =========================================== */
        
        QMainWindow {
            background-color: #f8fafc;
            font-family: "PingFang SC", "Microsoft YaHei", "Helvetica", "Arial", sans-serif;
        }
        
        /* ===========================================
           菜单栏样式
        =========================================== */
        
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #e2e8f0;
            padding: 4px 0px;
            font-size: 13px;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 6px 12px;
            margin: 0px 2px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #f1f5f9;
            color: #2563eb;
        }
        
        QMenuBar::item:pressed {
            background-color: #e2e8f0;
        }
        
        /* ===========================================
           工具栏样式
        =========================================== */
        
        QToolBar {
            background-color: white;
            border-bottom: 1px solid #e2e8f0;
            spacing: 8px;
            padding: 8px 16px;
        }
        
        QToolBar::separator {
            background-color: #e2e8f0;
            width: 1px;
            height: 24px;
            margin: 0px 8px;
        }
        
        /* ===========================================
           按钮样式
        =========================================== */
        
        QPushButton {
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 500;
            font-size: 13px;
            border: none;
            min-height: 24px;
        }
        
        QPushButton:hover {
            background-color: rgba(37, 99, 235, 0.1);
        }
        
        QPushButton:pressed {
            background-color: rgba(37, 99, 235, 0.2);
        }
        
        QPushButton#primaryButton {
            background-color: #2563eb;
            color: white;
        }
        
        QPushButton#primaryButton:hover {
            background-color: #1d4ed8;
        }
        
        QPushButton#primaryButton:pressed {
            background-color: #1e40af;
        }
        
        QPushButton#secondaryButton {
            background-color: #64748b;
            color: white;
        }
        
        QPushButton#secondaryButton:hover {
            background-color: #475569;
        }
        
        QPushButton#secondaryButton:pressed {
            background-color: #334155;
        }
        
        QPushButton#successButton {
            background-color: #059669;
            color: white;
        }
        
        QPushButton#successButton:hover {
            background-color: #047857;
        }
        
        QPushButton#successButton:pressed {
            background-color: #065f46;
        }
        
        QPushButton#warningButton {
            background-color: #d97706;
            color: white;
        }
        
        QPushButton#warningButton:hover {
            background-color: #b45309;
        }
        
        QPushButton#warningButton:pressed {
            background-color: #92400e;
        }
        
        QPushButton#dangerButton {
            background-color: #dc2626;
            color: white;
        }
        
        QPushButton#dangerButton:hover {
            background-color: #b91c1c;
        }
        
        QPushButton#dangerButton:pressed {
            background-color: #991b1b;
        }
        
        /* ===========================================
           面板和框架样式
        =========================================== */
        
        QFrame#leftPanel, QFrame#rightPanel {
            background-color: white;
            border-right: 1px solid #e2e8f0;
        }
        
        QFrame#rightPanel {
            border-right: none;
            border-left: 1px solid #e2e8f0;
        }
        
        QFrame#centerPanel {
            background-color: white;
        }
        
        QSplitter::handle {
            background-color: #e2e8f0;
            width: 1px;
            height: 1px;
        }
        
        QSplitter::handle:hover {
            background-color: #cbd5e1;
        }
        
        /* ===========================================
           标签和文本样式
        =========================================== */
        
        QLabel#groupTitle {
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 12px;
            padding-bottom: 4px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        QLabel#tableStatus {
            color: #6b7280;
            font-size: 13px;
            font-style: italic;
        }
        
        QLabel#infoValue {
            color: #374151;
            font-weight: 500;
            font-size: 13px;
        }
        
        QLabel#statLabel {
            color: #6b7280;
            font-size: 13px;
            min-width: 80px;
        }
        
        QLabel#statValue {
            color: #374151;
            font-weight: 600;
            font-size: 13px;
        }
        
        QLabel#legendText {
            color: #374151;
            font-size: 13px;
            margin-left: 8px;
        }
        
        QLabel#statusIndicator {
            font-size: 12px;
            margin-right: 6px;
        }
        
        /* ===========================================
           输入框样式
        =========================================== */
        
        QLineEdit {
            padding: 6px 12px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background-color: white;
            font-size: 13px;
            min-height: 16px;
        }
        
        QLineEdit:focus {
            border-color: #2563eb;
            outline: none;
            background-color: #fefefe;
        }
        
        QLineEdit:hover {
            border-color: #9ca3af;
        }
        
        /* ===========================================
           表格样式
        =========================================== */
        
        QTableWidget {
            gridline-color: #e5e7eb;
            background-color: white;
            alternate-background-color: #f9fafb;
            selection-background-color: #dbeafe;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            font-size: 13px;
        }
        
        QTableWidget::item {
            padding: 8px 12px;
            border: none;
            border-bottom: 1px solid #f3f4f6;
        }
        
        QTableWidget::item:selected {
            background-color: #dbeafe;
            color: #1e40af;
        }
        
        QTableWidget::item:hover {
            background-color: #f0f9ff;
        }
        
        QHeaderView::section {
            background-color: #f8fafc;
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid #e5e7eb;
            border-right: 1px solid #e5e7eb;
            font-weight: 600;
            font-size: 13px;
            color: #374151;
        }
        
        QHeaderView::section:first {
            border-top-left-radius: 8px;
        }
        
        QHeaderView::section:last {
            border-top-right-radius: 8px;
            border-right: none;
        }
        
        QHeaderView::section:hover {
            background-color: #f1f5f9;
        }
        
        /* ===========================================
           滚动条样式
        =========================================== */
        
        QScrollBar:vertical {
            background-color: #f3f4f6;
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #d1d5db;
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #9ca3af;
        }
        
        QScrollBar::handle:vertical:pressed {
            background-color: #6b7280;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
            background: none;
        }
        
        QScrollBar:horizontal {
            background-color: #f3f4f6;
            height: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #d1d5db;
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #9ca3af;
        }
        
        QScrollBar::handle:horizontal:pressed {
            background-color: #6b7280;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
            background: none;
        }
        
        /* ===========================================
           占位符样式
        =========================================== */
        
        QWidget#visualizationPlaceholder {
            background-color: #f8fafc;
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
        }
        
        QWidget#chartPlaceholder {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        QLabel#placeholderText {
            color: #9ca3af;
            font-size: 16px;
            font-weight: 500;
        }
        
        /* ===========================================
           状态指示器样式
        =========================================== */
        
        QLabel#statusIndicatorActive {
            color: #10b981;
        }
        
        QLabel#statusIndicatorWarning {
            color: #f59e0b;
        }
        
        QLabel#statusIndicatorError {
            color: #ef4444;
        }
        """
    
    @staticmethod
    def get_color_block_style(color):
        """获取颜色块样式"""
        return f"""
        QLabel {{
            background-color: {color};
            border-radius: 4px;
            border: 1px solid rgba(0, 0, 0, 0.1);
        }}
        """
