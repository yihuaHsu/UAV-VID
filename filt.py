#2024/04/02
import cv2
import numpy as np
import os
import cv2 as cv
import open3d as o3d
import math

def save_xy_file(point_cloud, filename):
    # 提取点云数据的 x 和 y 坐标
    points_xy = np.asarray(point_cloud.points)[:, :2]

    # 将点云数据保存到 .xy 文件
    with open(filename, "w") as file:
        for point in points_xy:
            # 将每个点的 x、y 坐标写入文件，每行一个点
            file.write(f"{point[0]} {point[1]}\n")

def video_screen_shot():
    video_file = 'book-test-rotate/book-video.mp4'   # 输入影片檔案名稱
    output_folder = 'output_frames-book'   # 输出資料夾名稱
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_file) # 打開影片文件
    # check
    if not cap.isOpened():
        print("Error: Unable to open video file.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)    # 取得影片幀率
    frame_interval = int(fps * 0.5)

    frame_count = 0
    total_frames = 0

    while cap.isOpened() and total_frames < 150:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            # 存圖像
            frame_file = os.path.join(output_folder, f'frame_{total_frames}.jpg')
            cv2.imwrite(frame_file, frame)
            print(f'Frame {total_frames} saved.')
            total_frames += 1
        frame_count += 1
    cap.release()
    print('Video frames extraction completed.')

def rotate_point(x, y, cx, cy, angle):
    # Convert angle to radians
    theta = math.radians(angle)
    # Perform rotation
    x_rotated = cx + (x - cx) * math.cos(theta) - (y - cy) * math.sin(theta)
    y_rotated = cy + (x - cx) * math.sin(theta) + (y - cy) * math.cos(theta)
    return x_rotated, y_rotated


folder_name = "UAV_path-book"  # 定義文件夾名稱
current_dir = os.path.dirname(os.path.realpath(__file__))
folder_path = os.path.join(current_dir, folder_name)   # 使用os.path.join連接路径和文件夾名稱
if not os.path.exists(folder_path):   # 檢查是否存在
    os.mkdir(folder_path)
    print(f"文件夾 '{folder_path}' 已創建。")
else:
    print(f"文件夾 '{folder_path}' 已存在。")



video_screen_shot()

MIN_MATCH_COUNT = 10
img3 = cv2.imread('book-test-rotate/book-test-01.jpg', 1) # trainImage
sift = cv2.SIFT_create() # 初始化 SIFT 檢測器

kp3, des3 = sift.detectAndCompute(img3, None) # 使用 SIFT 找到img3的關鍵點和描述子

# 定義 FLANN 參數
FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
search_params = dict(checks=50)

flann = cv2.FlannBasedMatcher(index_params, search_params)  # 創建 FLANN 匹配器


all_boxes = []  # 儲存所有方框的座標
center_points = []  # 儲存所有中心點座標
target_points = []
matched_points = []

average_keypoints_in_boxes = []  # 儲存每個方框的平均特徵點
farthest_keypoints_in_boxes = []  # 儲存每個方框內距離平均特徵點最遠的特徵點
distances = []  # 儲存每個方框內最遠特徵點與平均特徵點之間的距離
img_keypoints = []  # 儲存影像 img 的所有特徵點座標
total_path = 0
frame_count = 37

for i in range(0, frame_count):
    img = cv2.imread(f'output_frames-book/frame_{i}.jpg', 1)  # queryImage
    # 使用 SIFT 找到關鍵點和描述子
    kp1, des1 = sift.detectAndCompute(img, None)
    # 進行特徵匹配
    matches = flann.knnMatch(des1, des3, k=2)

    # 根據 Lowe's ratio 測試存儲所有良好的匹配
    good = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good.append(m)

    # 執行 Homography 變換
    if len(good) > MIN_MATCH_COUNT:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp3[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
        matchesMask = mask.ravel().tolist()

        # 計算旋轉角度（以度為單位）
        rotation_angle = np.arctan2(M[1, 0], M[0, 0]) * 180 / np.pi

        # 計算平移（以像素為單位）
        translation_x = M[0, 2]
        translation_y = M[1, 2]

        h, w, d = img.shape
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        dst = cv.perspectiveTransform(pts, M)

        x1, y1 = np.int32(dst[0][0])
        x2, y2 = np.int32(dst[1][0])
        x3, y3 = np.int32(dst[2][0])
        x4, y4 = np.int32(dst[3][0])
        center_x = (x1 + x2 + x3 + x4) / 4
        center_y = (y1 + y2 + y3 + y4) / 4

        # print("中心坐標為:", center_x, center_y)
        center_points.append((center_x, center_y))
        matched_points.append(src_pts.squeeze())
        target_points.append(dst_pts.squeeze())
        all_boxes.append(np.int32(dst))
        box_keypoints = []

        # MAP_Magnification()

        point_cloud = o3d.geometry.PointCloud()
        target_point_cloud = o3d.geometry.PointCloud()
        for points in matched_points:
            # 將每個特徵點轉換為 3D 點
            points_3d = np.hstack((points, np.zeros((points.shape[0], 1), dtype=np.float32)))
            # 將 3D 點添加到點雲中
            point_cloud.points.extend(o3d.utility.Vector3dVector(points_3d))
        for points in target_points:
            # 將每個特徵點轉換為 3D 點
            target_points_3d = np.hstack((points, np.zeros((points.shape[0], 1), dtype=np.float32)))
            # 將 3D 點添加到點雲中
            target_point_cloud.points.extend(o3d.utility.Vector3dVector(target_points_3d))

        save_xy_file(point_cloud, 'point_cloud.xy')
        save_xy_file(target_point_cloud, 'target_point_cloud.xy')


        print(rotation_angle)

        color = (0, 255, 0)  # BGR
        color2 = (0, 0, 255)  # BGR

        # 將所有中心點標示出來
        for point in center_points:
            center_x, center_y = map(int, point)
            cv.circle(img3, (center_x, center_y), radius=5, color=(255, 255, 255), thickness=25)

        #畫三角形
        center_x, center_y = map(int, center_points[i])
        base_length = 50
        half_base = base_length // 2
        height = int(0.866 * base_length)  # Height of an equilateral triangle is sqrt(3)/2 times the base length
        offset_factor = 50  # Adjust this value as needed
        # offset = offset_factor * angle / abs(angle) if angle != 0 else offset_factor

        # Calculate coordinates of base vertices
        vertex1 = (int(center_x - half_base - offset_factor), int(center_y + height))
        vertex2 = (int(center_x - offset_factor), int(center_y - height))
        vertex3 = (int(center_x + half_base - offset_factor), int(center_y + height))

        # Rotate the base vertices around the center point by a given angle (e.g., 45 degrees)
        # rotation_angle = 45  # Specify the rotation angle here
        vertex1_rotated = rotate_point(vertex1[0], vertex1[1], center_x, center_y, rotation_angle)
        vertex2_rotated = rotate_point(vertex2[0], vertex2[1], center_x, center_y, rotation_angle)
        vertex3_rotated = rotate_point(vertex3[0], vertex3[1], center_x, center_y, rotation_angle)

        # Draw the rotated triangle
        vertices_rotated = np.array([vertex1_rotated, vertex2_rotated, vertex3_rotated], dtype=np.int32)
        cv.fillPoly(img3, [vertices_rotated], color=(0+20*i, 255-20*i, 0))
        # 將所有中心點連接成直線
        for i in range(len(center_points) - 1):
            cv.line(img3, tuple(map(int, center_points[i])), tuple(map(int, center_points[i + 1])), color2, 10)
        #存進檔案中
        frame_file = os.path.join('UAV_path-book', f'path_{total_path}.jpg')
        cv2.imwrite(frame_file, img3)
        total_path += 1
        print("------------")
    else:
        print(f"Not enough matches are found in frame {i} - {len(good)}/{MIN_MATCH_COUNT}")








