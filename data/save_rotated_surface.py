import numpy as np
from surface import faces

def save_rotated_surface():
    points = np.asarray(faces, dtype=float)

    # 旋转 -90 度使开口朝向 Z 轴正方向 (原朝向 Y 负方向)
    # 绕 X 轴旋转 -90 度
    theta = np.radians(-90)
    c, s = np.cos(theta), np.sin(theta)
    # 绕 X 轴旋转矩阵
    R = np.array([
        [1, 0, 0],
        [0, c, -s],
        [0, s, c]
    ])
    # 应用旋转
    points = points @ R.T

    # 格式化输出
    output_path = "surface_rotated.py"
    
    print(f"Writing rotated faces to {output_path}...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("faces = [\n")
        # 为了保持格式整洁，每行写几个点，或者直接写
        # 原文件看起来是一行写3个点，或者紧凑格式
        # 这里简单起见，每行写一个点，或者保持紧凑
        
        # 转换为列表以便处理
        points_list = points.tolist()
        
        # 我们可以模仿原文件的格式，每行3个点
        chunk_size = 3
        for i in range(0, len(points_list), chunk_size):
            chunk = points_list[i:i + chunk_size]
            line_str = ""
            for p in chunk:
                # 保留4位小数，与原文件类似
                line_str += f"[{p[0]:.4f},{p[1]:.4f},{p[2]:.4f}],"
            f.write(line_str + "\n")
            
        f.write("]\n")
    
    print("Done.")

if __name__ == "__main__":
    save_rotated_surface()
