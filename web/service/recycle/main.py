import numpy as np
import cv2

from typing import List
from scipy.optimize import minimize


## 本身

from service.recycle.geo_transformer import geo_transformer
from service.recycle.schema import PointData


RANSACBOUND = 50.0


# **********
# Find homography function
# **********
def find_homography(
    pixels,
    pos3ds,
    camera_location,
    ransacbound,
):
    pixels = np.array(pixels)
    pos2 = np.zeros((len(pixels), 2))
    good = np.zeros(len(pixels))
    for i in range(len(pixels)):
        good[i] = pixels[i][0] != 0 or pixels[i][1] != 0
        p = pos3ds[i, :] - camera_location
        p = np.array([p[2], p[1], p[0]])
        p = p / p[2]
        pos2[i, :] = p[0:2]
    M, mask = cv2.findHomography(
        pos2[good == 1], np.array(pixels)[good == 1], cv2.RANSAC, ransacbound
    )

    M = np.linalg.inv(np.array(M, dtype=np.float64))
    err1 = 0
    err2 = 0
    # 新增：计算图像对角线长度用于归一化（假设图像尺寸已知）
    img_diagonal = np.linalg.norm([pixels[:, 0].max(), pixels[:, 1].max()])
    huber_delta = 0.1 * img_diagonal  # Huber损失阈值设为图像对角线的10%

    for i in range(pos2[good == 1].shape[0]):
        p1 = np.array(pixels)[good == 1][i, :]
        pp = np.array([pos2[good == 1][i, 0], pos2[good == 1][i, 1], 1.0])
        pp2 = np.matmul(np.linalg.inv(M), pp)
        pp2 = pp2 / pp2[2]
        P1 = np.array([p1[0], p1[1], 1.0])
        PP2 = np.matmul(M, P1)
        PP2 = PP2 / PP2[2]
        P2 = pos2[good == 1][i, :]

        # 计算Huber损失（替代原L2范数）
        error1 = np.linalg.norm(p1 - pp2[0:2])
        error2 = np.linalg.norm(P2 - PP2[0:2])

        # 归一化误差（除以图像对角线长度）
        error1_normalized = error1 / img_diagonal
        error2_normalized = error2 / img_diagonal

        # Huber损失计算
        huber_err1 = (
            0.5 * error1_normalized**2
            if error1_normalized <= huber_delta
            else huber_delta * (error1_normalized - 0.5 * huber_delta)
        )
        huber_err2 = (
            0.5 * error2_normalized**2
            if error2_normalized <= huber_delta
            else huber_delta * (error2_normalized - 0.5 * huber_delta)
        )

        if mask[i] == 1:
            err1 += huber_err1  # 内点使用Huber损失
            err2 += huber_err2
        else:
            # 外点使用实际误差的Huber损失（替代原固定值惩罚）
            err1 += huber_err1
            err2 += huber_err2

    return M, err1, err2, mask


def error_function(camera_pos, point_data):
    """输入相机3D坐标，输出err2（目标函数）"""
    # 调用find_homography计算当前位置的误差（需调整参数适配）
    _, err1, err2, _ = find_homography(
        pixels=np.array([r.pixel for r in point_data]),
        pos3ds=np.array([r.pos3d for r in point_data]),
        camera_location=camera_pos,
        ransacbound=RANSACBOUND,
    )
    return err1 * 10000 + err2 * 10000  # 调整权重以平衡err1和err2


def calculate(
    point_data: List[PointData],
):
    initial_pos = point_data[2].pos3d + 1

    # ---------------- 新增优化逻辑 ----------------

    # 替换原随机采样为拉丁超立方采样
    from scipy.stats import qmc  # 新增导入

    # 设置10公里搜索范围（10000米）
    search_radius = 10000

    num_initial_points = 5  # 可根据计算资源调整

    # 定义搜索空间边界
    bounds = [
        (initial_pos[0] - search_radius, initial_pos[0] + search_radius),
        (initial_pos[1] - search_radius, initial_pos[1] + search_radius),
        (initial_pos[2] - search_radius / 10, initial_pos[2] + search_radius / 10),
    ]

    # 拉丁超立方采样生成初始点（包含原始点）
    sampler = qmc.LatinHypercube(d=3)
    sample = sampler.random(n=num_initial_points - 1)  # 生成n-1个随机点
    initial_points = [initial_pos]  # 第一个点保留原始位置

    # 将采样点映射到实际搜索空间
    l_bounds = [b[0] for b in bounds]
    u_bounds = [b[1] for b in bounds]
    scaled_samples = qmc.scale(sample, l_bounds, u_bounds)  # shape: (n-1, 3)
    for i in range(num_initial_points - 1):
        initial_points.append(np.array(scaled_samples[i]))

    # 多初始点优化搜索
    best_result = None
    best_error = np.inf
    bounds = [
        (initial_pos[0] - search_radius, initial_pos[0] + search_radius),
        (initial_pos[1] - search_radius, initial_pos[1] + search_radius),
        (
            (
                initial_pos[2] - search_radius / 10
                if initial_pos[2] - search_radius / 10 > 0
                else 0
            ),
            initial_pos[2] + search_radius / 10,
        ),
    ]

    best_result = None
    best_error = np.inf

    for idx, start_pos in enumerate(initial_points):
        print(f"\n===== 正在优化第 {idx + 1}/{num_initial_points} 个初始点 =====")
        print(f"初始点坐标: {start_pos}")

        # ---------------- 替换为全局+局部优化组合 ----------------
        from scipy.optimize import differential_evolution  # 新增导入

        # 第一阶段：全局优化（差分进化算法）
        print("===== 正在执行全局优化（差分进化） =====")
        global_result = differential_evolution(
            func=error_function,
            args=(point_data,),
            bounds=bounds,
            strategy="best1bin",  # 经典策略
            maxiter=2000,  # 最大迭代次数
            popsize=20,  # 种群大小（影响搜索广度）
            tol=0.0001,  # 收敛阈值
            mutation=(0.5, 1),  # 变异参数
            recombination=0.7,  # 重组概率
            workers=-1,  # 使用所有可用CPU核心
            polish=False,  # 暂不启用局部细化（后续用局部优化器处理）
            updating="deferred",  # 延迟更新策略
        )

        # 第二阶段：局部优化细化（使用全局优化结果作为初始点）
        print("\n===== 正在执行局部优化细化 =====")
        local_result = minimize(
            fun=error_function,
            args=(point_data,),
            x0=global_result.x,
            method="BFGS",  # 也可替换为L-BFGS-B等梯度优化器
            options={"disp": True, "maxiter": 3000},
        )

        # 更新最优结果
        if local_result.fun < best_error:
            best_error = local_result.fun
            best_result = local_result
            print(f"找到更优解！当前最小误差: {best_error}")
            print(f"当前最优位置: {best_result.x}")

    # 最终优化结果
    if best_result is not None and hasattr(best_result, "x"):
        optimized_pos = best_result.x  # 优化后的相机位置
    else:
        raise RuntimeError(
            "优化未找到有效结果，best_result为None。请检查优化过程或参数设置。"
        )

    M, _, _, _ = find_homography(
        pixels=np.array([r.pixel for r in point_data]),
        pos3ds=np.array([r.pos3d for r in point_data]),
        camera_location=optimized_pos,
        ransacbound=RANSACBOUND,
    )
    print("优化后位置误差:", best_error)
    print(f"优化后相机位置: {optimized_pos}")

    position = geo_transformer.utm_to_wgs84(optimized_pos[0], optimized_pos[1])

    return position
