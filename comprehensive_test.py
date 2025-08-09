#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合系统测试脚本
测试所有主要功能组件的基本运行状态
"""

import sys
import os
import time
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        print("  ✅ PySide6 导入成功")
    except ImportError as e:
        print(f"  ❌ PySide6 导入失败: {e}")
        return False
    
    try:
        import config
        print("  ✅ config 模块导入成功")
    except ImportError as e:
        print(f"  ❌ config 模块导入失败: {e}")
        return False
        
    try:
        import styles
        print("  ✅ styles 模块导入成功")
    except ImportError as e:
        print(f"  ❌ styles 模块导入失败: {e}")
        return False
        
    try:
        import data_manager
        print("  ✅ data_manager 模块导入成功")
    except ImportError as e:
        print(f"  ❌ data_manager 模块导入失败: {e}")
        return False
    
    try:
        import main_window
        print("  ✅ main_window 模块导入成功")
    except ImportError as e:
        print(f"  ❌ main_window 模块导入失败: {e}")
        return False
    
    return True

def test_config():
    """测试配置模块"""
    print("🔍 测试配置模块...")
    
    try:
        import config
        app_config = config.AppConfig()
        
        # 测试基本属性
        assert hasattr(app_config, 'window_title')
        assert hasattr(app_config, 'window_size')
        assert hasattr(app_config, 'colors')
        print("  ✅ 配置对象属性完整")
        
        # 测试颜色配置
        colors = app_config.colors
        required_colors = ['qualified', 'attention', 'exceeded', 'background']
        for color in required_colors:
            assert color in colors, f"缺少颜色配置: {color}"
        print("  ✅ 颜色配置完整")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置模块测试失败: {e}")
        return False

def test_styles():
    """测试样式模块"""
    print("🔍 测试样式模块...")
    
    try:
        import styles
        
        # 测试样式函数
        main_style = styles.get_main_window_style()
        assert isinstance(main_style, str), "主窗口样式应为字符串"
        assert len(main_style) > 0, "主窗口样式不能为空"
        print("  ✅ 主窗口样式生成成功")
        
        toolbar_style = styles.get_toolbar_style()
        assert isinstance(toolbar_style, str), "工具栏样式应为字符串"
        print("  ✅ 工具栏样式生成成功")
        
        table_style = styles.get_table_style()
        assert isinstance(table_style, str), "表格样式应为字符串"
        print("  ✅ 表格样式生成成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 样式模块测试失败: {e}")
        return False

def test_data_manager():
    """测试数据管理模块"""
    print("🔍 测试数据管理模块...")
    
    try:
        import data_manager
        
        # 测试数据点类
        point = data_manager.MeasurementPoint(10.0, 20.0, 30.0, 0.05, "合格")
        assert point.x == 10.0
        assert point.y == 20.0
        assert point.z == 30.0
        assert point.deviation == 0.05
        assert point.status == "合格"
        print("  ✅ MeasurementPoint 类测试成功")
        
        # 测试统计类
        stats = data_manager.MeasurementStatistics()
        stats.total_points = 100
        stats.qualified_count = 85
        stats.attention_count = 10
        stats.exceeded_count = 5
        
        assert stats.total_points == 100
        assert stats.qualified_count == 85
        print("  ✅ MeasurementStatistics 类测试成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 数据管理模块测试失败: {e}")
        return False

def test_main_window_creation():
    """测试主窗口创建"""
    print("🔍 测试主窗口创建...")
    
    try:
        from PySide6.QtWidgets import QApplication
        import main_window
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 创建主窗口
        window = main_window.MainWindow()
        
        # 测试基本属性
        assert hasattr(window, 'central_widget')
        assert hasattr(window, 'measurement_table')
        assert hasattr(window, 'simulation_timer')
        print("  ✅ 主窗口基本组件创建成功")
        
        # 测试菜单和工具栏
        assert window.menuBar() is not None
        assert len(window.findChildren(type(window.menuBar().children()[0]))) > 0
        print("  ✅ 菜单栏创建成功")
        
        # 测试左侧面板
        assert hasattr(window, 'left_panel')
        assert hasattr(window, 'x_start_input')
        assert hasattr(window, 'x_end_input')
        print("  ✅ 左侧参数面板创建成功")
        
        # 测试右侧面板
        assert hasattr(window, 'right_panel')
        assert hasattr(window, 'total_points_label')
        assert hasattr(window, 'qualified_count_label')
        print("  ✅ 右侧统计面板创建成功")
        
        # 关闭窗口
        window.close()
        
        return True
        
    except Exception as e:
        print(f"  ❌ 主窗口创建测试失败: {e}")
        traceback.print_exc()
        return False

def test_file_structure():
    """测试文件结构完整性"""
    print("🔍 测试项目文件结构...")
    
    required_files = [
        'app.py',
        'main_window.py',
        'config.py', 
        'styles.py',
        'data_manager.py',
        'requirements.txt',
        'README.md',
        'QUICK_START.md',
        'DEV_GUIDE.md',
        'API_REFERENCE.md',
        'FUNCTIONS.md',
        'ARCHITECTURE.md',
        'TROUBLESHOOTING.md',
        'CHANGELOG.md',
        'DOC_INDEX.md',
        'run.sh',
        'install.sh'
    ]
    
    missing_files = []
    for file in required_files:
        if not (project_root / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"  ❌ 缺少文件: {', '.join(missing_files)}")
        return False
    else:
        print(f"  ✅ 所有必需文件存在 ({len(required_files)} 个)")
        return True

def test_documentation():
    """测试文档完整性"""
    print("🔍 测试文档完整性...")
    
    try:
        # 检查README内容
        readme_path = project_root / 'README.md'
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        required_sections = ['项目概述', '主要功能', '快速开始', '项目结构']
        missing_sections = []
        for section in required_sections:
            if section not in readme_content:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"  ⚠️  README.md 缺少章节: {', '.join(missing_sections)}")
        else:
            print("  ✅ README.md 内容完整")
        
        # 检查文档索引
        doc_index_path = project_root / 'DOC_INDEX.md'
        with open(doc_index_path, 'r', encoding='utf-8') as f:
            doc_index_content = f.read()
        
        if 'TROUBLESHOOTING.md' in doc_index_content and 'CHANGELOG.md' in doc_index_content:
            print("  ✅ 文档索引已更新")
        else:
            print("  ⚠️  文档索引可能需要更新")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 文档测试失败: {e}")
        return False

def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 开始综合系统测试...\n")
    
    tests = [
        ("模块导入测试", test_imports),
        ("配置模块测试", test_config),
        ("样式模块测试", test_styles),
        ("数据管理测试", test_data_manager),
        ("主窗口创建测试", test_main_window_creation),
        ("文件结构测试", test_file_structure),
        ("文档完整性测试", test_documentation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                failed += 1
                print(f"❌ {test_name} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 异常: {e}")
            traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print("=" * 50)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")
    print(f"🎯 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过！系统状态良好。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要检查。")
        return False

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚡ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 测试过程发生异常: {e}")
        traceback.print_exc()
        sys.exit(1)
