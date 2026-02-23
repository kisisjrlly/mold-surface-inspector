#!/usr/bin/env python3
"""
系统集成测试脚本

测试各组件的连通性：
1. Modbus 仿真器连接测试
2. 探头测量数据读取测试
3. 理论点云加载测试
4. WebSocket 服务器测试
"""

import sys
import time

def test_modbus_simulator():
    """测试 Modbus 仿真器连接"""
    print("\n" + "="*50)
    print("测试 1: Modbus 仿真器连接")
    print("="*50)
    
    try:
        from hardware_driver import PLCDriver
        
        driver = PLCDriver(ip='127.0.0.1', port=502)
        
        if driver.connect():
            print("✓ 成功连接到 Modbus 仿真器")
            
            # 测试读取系统状态
            status = driver.get_system_status()
            print(f"✓ 系统状态: {status}")
            
            # 测试读取运动参数
            motion = driver.get_motion_parameters()
            print(f"✓ 运动参数: 角度={motion.get('angle', 'N/A')}°, "
                  f"水平位置={motion.get('horizontal_position', 'N/A')}mm")
            
            # 测试读取探头测量数据
            probes = driver.get_probe_measurements()
            print(f"✓ 探头测量: 1#={probes.get('probe1', 0):.3f}mm, "
                  f"2#={probes.get('probe2', 0):.3f}mm")
            
            driver.disconnect()
            print("✓ Modbus 仿真器测试通过")
            return True
        else:
            print("✗ 无法连接到 Modbus 仿真器")
            print("  请确保已运行: python modbus_sim_server.py")
            return False
            
    except Exception as e:
        print(f"✗ Modbus 测试失败: {e}")
        return False


def test_theoretical_data_loading():
    """测试理论点云加载"""
    print("\n" + "="*50)
    print("测试 2: 理论点云数据加载")
    print("="*50)
    
    try:
        import numpy as np
        import pandas as pd
        import os
        
        # 测试 CSV 格式
        csv_file = os.path.join('data', 'semicylinder_pointcloud.csv')
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            print(f"✓ CSV 文件加载成功: {len(df)} 个点")
            print(f"  列名: {df.columns.tolist()}")
            print(f"  范围: X=[{df['x_mm'].min():.1f}, {df['x_mm'].max():.1f}], "
                  f"Y=[{df['y_mm'].min():.1f}, {df['y_mm'].max():.1f}], "
                  f"Z=[{df['z_mm'].min():.1f}, {df['z_mm'].max():.1f}]")
        else:
            print(f"  跳过 CSV 测试: {csv_file} 不存在")
        
        # 测试 Python 格式
        py_file = os.path.join('data', 'surface_rotated.py')
        if os.path.exists(py_file):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            local_vars = {}
            exec(content, {}, local_vars)
            if 'faces' in local_vars:
                faces = local_vars['faces']
                points = np.array(faces)
                unique_points = np.unique(points, axis=0)
                print(f"✓ Python 文件加载成功: {len(unique_points)} 个唯一点（原始 {len(faces)} 个）")
                print(f"  范围: X=[{unique_points[:,0].min():.1f}, {unique_points[:,0].max():.1f}], "
                      f"Y=[{unique_points[:,1].min():.1f}, {unique_points[:,1].max():.1f}], "
                      f"Z=[{unique_points[:,2].min():.1f}, {unique_points[:,2].max():.1f}]")
            else:
                print("✗ Python 文件中没有 faces 变量")
        else:
            print(f"  跳过 Python 测试: {py_file} 不存在")
        
        print("✓ 理论点云数据测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 理论点云测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_point_matching():
    """测试理论点与测量点匹配"""
    print("\n" + "="*50)
    print("测试 3: 点云匹配算法")
    print("="*50)
    
    try:
        import numpy as np
        from scipy.spatial import cKDTree
        
        # 创建测试数据
        theoretical = np.array([
            [0, 0, 200],
            [10, 0, 199.75],
            [20, 0, 199],
            [30, 0, 197.75],
        ])
        
        # 创建 KD-Tree
        tree = cKDTree(theoretical)
        
        # 测试查询点
        query_point = np.array([9.5, 0.5, 199.5])
        distance, idx = tree.query(query_point)
        
        print(f"✓ 查询点: {query_point}")
        print(f"  最近理论点: {theoretical[idx]}")
        print(f"  距离: {distance:.4f}mm")
        print(f"  偏差 (测量-理论): {np.linalg.norm(query_point - theoretical[idx]):.4f}mm")
        
        print("✓ 点云匹配算法测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 点云匹配测试失败: {e}")
        return False


def test_websocket_server():
    """测试 WebSocket 服务器（不启动，只检查模块）"""
    print("\n" + "="*50)
    print("测试 4: WebSocket 服务器模块")
    print("="*50)
    
    try:
        from electron_ws_server import DualProbeScanServer
        
        # 创建实例（不启动）
        server = DualProbeScanServer()
        
        print("✓ WebSocket 服务器模块加载成功")
        print(f"  支持的命令: connect, disconnect, start_scan, stop_scan, "
              "reset_system, load_theoretical, emergency_stop")
        
        # 测试理论点云加载方法
        import os
        csv_file = os.path.join('data', 'semicylinder_pointcloud.csv')
        if os.path.exists(csv_file):
            result = server.load_theoretical_data(csv_file)
            if result:
                print(f"✓ 理论点云加载方法测试成功: {len(server.theoretical_data)} 个点")
            else:
                print("✗ 理论点云加载方法失败")
        
        print("✓ WebSocket 服务器模块测试通过")
        return True
        
    except Exception as e:
        print(f"✗ WebSocket 服务器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("       模具表面检测系统 - 集成测试")
    print("="*60)
    
    results = []
    
    # 测试 Modbus（可能失败，如果仿真器未启动）
    results.append(("Modbus 仿真器", test_modbus_simulator()))
    
    # 测试理论点云加载
    results.append(("理论点云加载", test_theoretical_data_loading()))
    
    # 测试点云匹配
    results.append(("点云匹配算法", test_point_matching()))
    
    # 测试 WebSocket 模块
    results.append(("WebSocket 模块", test_websocket_server()))
    
    # 打印摘要
    print("\n" + "="*60)
    print("测试摘要")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    print("-"*60)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n所有测试通过！系统准备就绪。")
    else:
        print("\n部分测试失败，请检查相关组件。")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
