<template>
  <div class="container">
    <div class="canvas-container-wrapper" ref="canvasContainerWrapper">
      <CanvasViewer
        :image="currentImage"
        :show-coordinates="true"
        :points="points"
        :custom-mouse-down-handler="handleCustomMouseDown"
        @pointsLoaded="handlePointsLoaded"
      />
    </div>
    <div class="control-panel">
      <div class="image-selector-container">
        <label class="input-label">选择历史照片</label>
        <el-select
          v-model="currentImage"
          placeholder="请选择历史照片"
          class="w-full"
          :loading="isLoadingImages"
          filterable
          clearable
          value-key="id"
          @change="handleImageSelect"
        >
          <template #suffix>
            <el-button
              size="small"
              :loading="isLoadingImages"
              @click="refreshImages"
            >
              刷新
            </el-button>
          </template>
          <el-option
            v-for="image in allImages"
            :key="image.id"
            :label="image.name"
            :value="image"
          >
            {{ image.name }}
          </el-option>
        </el-select>
        <div class="status-text">{{ imageStatusText }}</div>
      </div>

      <!-- 建筑点选择器 -->
      <div class="image-selector-container">
        <label class="input-label">选择建筑点</label>
        <el-select
          v-model="selectedBuildingPoint"
          placeholder="请选择建筑点"
          class="w-full"
          :loading="isLoadingBuildingPoints"
          filterable
          clearable
          value-key="id"
        >
          <el-option
            v-for="buildingPoint in buildingPoints"
            :key="buildingPoint.id"
            :label="buildingPoint.name"
            :value="buildingPoint"
          >
            {{ buildingPoint.name }} ({{ buildingPoint.latitude }},
            {{ buildingPoint.longitude }})
          </el-option>
        </el-select>
        <div class="status-text" v-if="selectedBuildingPoint">
          已选择建筑点: {{ selectedBuildingPoint.name }}
          <span style="color: green; font-size: 12px; margin-left: 10px">
            ✓ 点击图片添加该建筑点
          </span>
        </div>
      </div>

      <el-button @click="async () => await saveAnnotations()">
        保存标注
      </el-button>
      <PointList :points="points" @removePoint="removePoint" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { showErrorMessage, get, post } from "../utils/request";
import type { Point, Image } from "../utils/types";

import PointList from "../components/PointList.vue";
import CanvasViewer from "../components/CanvasViewer.vue";

// 定义建筑点类型
interface BuildingPoint {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

// 状态管理
const points = ref<Point[]>([]);
const currentImage = ref<Image | null>(null);
const allImages = ref<Image[]>([]);
const isLoadingImages = ref(false);
const imageStatusText = ref("未选择照片");
const currentImageName = ref("");
const canvasContainerWrapper = ref<HTMLDivElement | null>(null);

// 建筑点相关状态
const buildingPoints = ref<BuildingPoint[]>([]);
// 修复selectedBuildingPoint的类型定义，确保正确显示选中项
const selectedBuildingPoint = ref<BuildingPoint | null>(null);
const isLoadingBuildingPoints = ref(false);
// 获取建筑点列表
const fetchBuildingPoints = async () => {
  try {
    isLoadingBuildingPoints.value = true;
    const response = await get<BuildingPoint[]>("/api/building_points");
    buildingPoints.value = response.data;
  } catch (error) {
    console.error("获取建筑点列表失败:", error);
    showErrorMessage("获取建筑点列表失败，请稍后重试", "加载失败");
  } finally {
    isLoadingBuildingPoints.value = false;
  }
};

// 页面加载完成后立即尝试获取图片列表和建筑点列表
onMounted(async () => {
  // 获取图片列表
  await refreshImages();
  // 获取建筑点列表
  await fetchBuildingPoints();
});

// 刷新图片列表
async function refreshImages() {
  isLoadingImages.value = true;
  try {
    const response = await get<Image[]>("/api/images");
    allImages.value = response.data;
    imageStatusText.value = `共找到 ${allImages.value.length} 张照片`;
  } catch (error) {
    console.error("获取图片列表失败:", error);
    imageStatusText.value = "获取图片列表失败";
    showErrorMessage("获取图片列表失败，请稍后重试", "加载失败");
  } finally {
    isLoadingImages.value = false;
  }
}

// 通过Select选择图片处理
function handleImageSelect(selected: Image | null) {
  if (!selected) {
    imageStatusText.value = "未选择照片";
    currentImage.value = null;
    currentImageName.value = "";
    return;
  }

  currentImage.value = selected;
  currentImageName.value = selected.name;
  imageStatusText.value = selected.name;
}

// 处理特征点加载完成事件
function handlePointsLoaded(newPoints: Point[]) {
  points.value = newPoints;
}

// 自定义鼠标点击处理函数
const handleCustomMouseDown = (
  event: MouseEvent,
  coordinates: { x: number; y: number }
) => {
  // 如果有选中的建筑点，则使用建筑点信息创建新点
  if (selectedBuildingPoint.value) {
    if (!currentImage.value) {
      showErrorMessage("请先选择历史照片", "操作失败");
      return false;
    }
    const newPoint: Point = {
      id: points.value.length + 1, // 服务器会生成ID
      pixel_x: coordinates.x,
      pixel_y: coordinates.y,
      name: selectedBuildingPoint.value.name,
      longitude: selectedBuildingPoint.value.longitude.toString(),
      latitude: selectedBuildingPoint.value.latitude.toString(),
      image_id: currentImage.value.id,
      building_point_id: selectedBuildingPoint.value.id,
    };

    // 检查点是否重复
    const isDuplicate = points.value.some(
      (point) =>
        Math.abs(point.pixel_x - coordinates.x) <= 5 &&
        Math.abs(point.pixel_y - coordinates.y) <= 5
    );

    if (!isDuplicate) {
      points.value.push(newPoint);
      // 为了确保Vue能检测到数组变化，创建一个新的数组引用
      points.value = [...points.value];
    } else {
      showErrorMessage("该位置已有点，无法重复添加", "添加失败");
    }
  }

  return false;
};

// 删除点
function removePoint(index: number) {
  points.value.splice(index, 1);
  points.value = [...points.value];
}

// 保存标注信息
async function saveAnnotations() {
  if (!currentImage.value || !currentImageName.value) {
    showErrorMessage("请先选择历史照片", "操作失败");
    return;
  }

  try {
    // 转换标注点格式为后端需要的格式
    const featuresData = {
      features: points.value.map((point) => ({
        x: point.pixel_x,
        y: point.pixel_y,
        image_id: currentImage.value!.id,
        building_point_id: point.building_point_id,
        longitude: point.longitude,
        latitude: point.latitude,
      })),
    };

    // 发送到后端保存
    const response = await post<{ message: string }>(
      "/api/upload_features",
      featuresData
    );

    showErrorMessage(`${response.data.message}`, `保存成功`, "info");
  } catch (error) {
    showErrorMessage("保存标注信息失败，请稍后重试", "保存失败");
    console.error("保存标注错误:", error);
  }
}
</script>

<style scoped>
.container {
  display: flex;
  width: 100%;
  height: calc(100vh - 10vh);
  gap: 20px;
}

.canvas-container-wrapper {
  position: relative;
  flex: 1;
  overflow: hidden;
  min-width: 0; /* 防止canvas溢出 */
}

.control-panel {
  width: 300px;
  padding: 15px;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
  gap: 15px; /* 统一间距 */
  flex-shrink: 0; /* 防止面板被压缩 */
}

.input-field {
  padding: 8px;
  width: calc(100% - 16px); /* 统一宽度 */
  border: 1px solid #ddd;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.input-field:hover {
  background-color: #f0f0f0;
}

.input-field:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* 图片选择器样式 */
.image-selector-container {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.status-text {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

/* Element Plus 组件样式调整 */
:deep(.el-autocomplete) {
  width: 100%;
}

:deep(.el-input__wrapper) {
  border-radius: 4px;
}

:deep(.el-input-group__append) {
  padding: 0 8px;
}
</style>
