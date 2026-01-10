import numpy as np
import matplotlib.pyplot as plt

from surface_rotated import faces


def plot_surface_points():
	points = np.asarray(faces, dtype=float)

	# # 旋转 -90 度使开口朝向 Z 轴正方向 (原朝向 Y 负方向)
	# # 绕 X 轴旋转 -90 度
	# theta = np.radians(-90)
	# c, s = np.cos(theta), np.sin(theta)
	# # 绕 X 轴旋转矩阵
	# R = np.array([
	# 	[1, 0, 0],
	# 	[0, c, -s],
	# 	[0, s, c]
	# ])
	# # 应用旋转 (points 是 N x 3，需要转置或者右乘 R 的转置)
	# points = points @ R.T

	fig = plt.figure()
	ax = fig.add_subplot(111, projection="3d")
	ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=2, c=points[:, 2], cmap="viridis", linewidth=0)

	ax.set_xlabel("X")
	ax.set_ylabel("Y")
	ax.set_zlabel("Z")

	# keep the plot roughly isotropic so the shape is not distorted
	span = points.max(axis=0) - points.min(axis=0)
	print(f"Max distance -> X: {span[0]:.3f}, Y: {span[1]:.3f}, Z: {span[2]:.3f}")
	max_range = span.max()
	center = points.mean(axis=0)
	for setter, mid in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), center):
		half = max_range / 2
		setter(mid - half, mid + half)

	plt.tight_layout()
	plt.show()


if __name__ == "__main__":
	plot_surface_points()
