#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半圆柱体理论点云生成器

生成一个完美光滑的半圆柱体曲面点云数据：
- 长度: 2000mm (X轴)
- 直径: 1000mm (半径500mm)
- 采样间隔: 10mm
"""

import numpy as np
import csv
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def generate_semicylinder_pointcloud():
    """生成半圆柱体点云数据"""
    
    # 几何参数
    length = 2000.0      # 长度 2米 (mm)
    radius = 500.0       # 半径 500mm (直径1米)
    step = 10.0          # 采样间隔 10mm
    
    # 计算采样点数
    x_points = int(length / step) + 1
    theta_points = int(np.pi * radius / step) + 1  # 半圆弧长对应的点数
    
    print(f"Generating semicylinder point cloud...")
    print(f"Length: {length}mm, Radius: {radius}mm, Step: {step}mm")
    print(f"Points: {x_points} x {theta_points} = {x_points * theta_points} total points")
    
    # 生成点云数据
    points = []
    
    for i in range(x_points):
        x = i * step  # X坐标
        
        for j in range(theta_points):
            theta = j * np.pi / (theta_points - 1)  # 角度从0到π
            
            # 半圆柱体参数方程
            y = radius * np.cos(theta)  # Y坐标
            z = radius * np.sin(theta)  # Z坐标
            
            points.append([x, y, z])
    
    return points

def save_pointcloud(points, filename="data/semicylinder_pointcloud.csv"):
    """保存点云数据到CSV文件"""
    
    import os
    
    # 确保data目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    print(f"Saving {len(points)} points to {filename}...")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 写入CSV头部（只包含x,y,z坐标）
        writer.writerow(['x_mm', 'y_mm', 'z_mm'])
        
        # 写入数据（只写x,y,z坐标）
        for point in points:
            writer.writerow([f"{point[0]:.3f}", f"{point[1]:.3f}", f"{point[2]:.3f}"])
    
    print(f"Point cloud saved successfully!")

def plot_pointcloud(points, sample_ratio=0.1):
    """绘制3D点云图形"""
    
    print(f"Creating 3D visualization...")
    
    # 为了提高显示性能，对点云进行采样
    if len(points) > 2000:
        sample_size = max(1000, int(len(points) * sample_ratio))
        indices = np.random.choice(len(points), sample_size, replace=False)
        sampled_points = [points[i] for i in sorted(indices)]
        print(f"Sampling {len(sampled_points)} points from {len(points)} total points")
    else:
        sampled_points = points
    
    # 提取坐标
    x_coords = [p[0] for p in sampled_points]
    y_coords = [p[1] for p in sampled_points] 
    z_coords = [p[2] for p in sampled_points]
    
    # 创建3D图形
    fig = plt.figure(figsize=(12, 9))
    
    # 3D散点图
    ax1 = fig.add_subplot(221, projection='3d')
    scatter = ax1.scatter(x_coords, y_coords, z_coords, 
                         c=z_coords, cmap='viridis', s=2, alpha=0.6)
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.set_zlabel('Z (mm)')
    ax1.set_title('Semicylinder Point Cloud - 3D View')
    fig.colorbar(scatter, ax=ax1, shrink=0.5)
    
    # XY平面投影 (顶视图)
    ax2 = fig.add_subplot(222)
    ax2.scatter(x_coords, y_coords, c=z_coords, cmap='viridis', s=2, alpha=0.6)
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.set_title('XY Plane Projection (Top View)')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    
    # XZ平面投影 (侧视图)
    ax3 = fig.add_subplot(223)
    ax3.scatter(x_coords, z_coords, c=y_coords, cmap='plasma', s=2, alpha=0.6)
    ax3.set_xlabel('X (mm)')
    ax3.set_ylabel('Z (mm)') 
    ax3.set_title('XZ Plane Projection (Side View)')
    ax3.grid(True, alpha=0.3)
    
    # YZ平面投影 (端视图)
    ax4 = fig.add_subplot(224)
    ax4.scatter(y_coords, z_coords, c=x_coords, cmap='coolwarm', s=2, alpha=0.6)
    ax4.set_xlabel('Y (mm)')
    ax4.set_ylabel('Z (mm)')
    ax4.set_title('YZ Plane Projection (End View)')
    ax4.grid(True, alpha=0.3)
    ax4.set_aspect('equal')
    
    plt.tight_layout()
    
    # 确保figures目录存在
    import os
    os.makedirs('figures', exist_ok=True)
    
    # 保存图像
    plt.savefig('figures/semicylinder_pointcloud.png', dpi=300, bbox_inches='tight')
    print("3D visualization saved as: figures/semicylinder_pointcloud.png")

    # 显示图形
    plt.show()

def main():
    """主函数"""
    print("=" * 50)
    print("Semicylinder Point Cloud Generator")
    print("=" * 50)
    
    # 生成点云
    points = generate_semicylinder_pointcloud()
    
    # 保存数据
    save_pointcloud(points)
    
    # 绘制3D可视化
    plot_pointcloud(points)
    
    # 显示统计信息
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    z_coords = [p[2] for p in points]
    
    print("\nPoint Cloud Statistics:")
    print(f"Total points: {len(points)}")
    print(f"X range: {min(x_coords):.1f} to {max(x_coords):.1f} mm")
    print(f"Y range: {min(y_coords):.1f} to {max(y_coords):.1f} mm")
    print(f"Z range: {min(z_coords):.1f} to {max(z_coords):.1f} mm")
    print("\nOutput file: data/semicylinder_pointcloud.csv")
    print("Done!")

if __name__ == "__main__":
    main()
