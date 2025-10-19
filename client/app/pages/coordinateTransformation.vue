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
          @change="handleBuildingPointSelect"
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
      </div>

      <!-- 地理坐标转像素坐标 -->
      <div class="transformation-section">
        <h3>地理坐标转像素坐标</h3>
        <div class="input-group">
          <label>经度:</label>
          <el-input
            v-model="geoLongitude"
            type="number"
            placeholder="请输入经度"
            :disabled="!currentImage"
          />
        </div>
        <div class="input-group">
          <label>纬度:</label>
          <el-input
            v-model="geoLatitude"
            type="number"
            placeholder="请输入纬度"
            :disabled="!currentImage"
          />
        </div>
        <el-button
          @click="calculateGeoToPixel"
          :disabled="!currentImage || !geoLongitude || !geoLatitude"
        >
          转换为像素坐标
        </el-button>
      </div>

      <!-- 结果显示 -->
      <div v-if="pixelResult" class="result-section">
        <h3>转换结果</h3>
        <div class="result-item">
          <strong>像素坐标:</strong> ({{ pixelResult.x }}, {{ pixelResult.y }})
        </div>
        <div v-if="geoResult" class="result-item">
          <strong>地理坐标:</strong> ({{ geoResult.longitude }},
          {{ geoResult.latitude }})
        </div>
      </div>

      <div class="instructions">
        <p><strong>使用说明:</strong></p>
        <ul>
          <li>点击图片上的位置可获取地理坐标</li>
          <li>输入地理坐标或选择建筑点可在图片上标注位置</li>
          <li>选择建筑点后，系统会自动填充地理坐标</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { showErrorMessage, get, post } from "../utils/request";
import type { Point, Image } from "../utils/types";
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
const canvasContainerWrapper = ref<HTMLDivElement | null>(null);

// 建筑点相关状态
const buildingPoints = ref<BuildingPoint[]>([]);
const selectedBuildingPoint = ref<BuildingPoint | null>(null);
const isLoadingBuildingPoints = ref(false);

// 坐标转换相关状态
const geoLongitude = ref<string>("");
const geoLatitude = ref<string>("");
const pixelResult = ref<{ x: number; y: number } | null>(null);
const geoResult = ref<{ longitude: string; latitude: string } | null>(null);

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
    points.value = [];
    return;
  }

  currentImage.value = selected;
  imageStatusText.value = selected.name;
  points.value = [];
}

// 处理建筑点选择
function handleBuildingPointSelect(selected: BuildingPoint | null) {
  if (!selected) {
    selectedBuildingPoint.value = null;
    return;
  }

  selectedBuildingPoint.value = selected;
  geoLongitude.value = selected.longitude.toString();
  geoLatitude.value = selected.latitude.toString();
}

// 处理特征点加载完成事件
function handlePointsLoaded(newPoints: Point[]) {
  points.value = newPoints;
}

// 自定义鼠标点击处理函数 - 用于像素转地理坐标
const handleCustomMouseDown = async (
  event: MouseEvent,
  coordinates: { x: number; y: number }
) => {
  if (!currentImage.value) {
    showErrorMessage("请先选择历史照片", "操作失败");
    return false;
  }

  try {
    // 调用API将像素坐标转换为地理坐标
    // 转换参数格式为后端期望的元组格式 [x, y]
    console.log(coordinates);
    const pixels = [coordinates.x, coordinates.y];
    const response = await post<any>(
      `/api/calculate_pixel_to_geo/${currentImage.value.id}`,
      pixels
    );

    if (response.status === 200) {
      const geoPoint = response.data.geo;
      geoResult.value = {
        longitude: geoPoint[0].toString(),
        latitude: geoPoint[1].toString(),
      };

      showErrorMessage(
        `坐标转换成功:经度 ${geoResult.value.longitude}, 纬度 ${geoResult.value.latitude}`,
        "操作成功",
        "info"
      );
    } else {
      showErrorMessage("坐标转换失败", "操作失败");
    }
  } catch (error) {
    console.error("像素转地理坐标失败:", error);
    showErrorMessage("像素转地理坐标失败，请稍后重试", "操作失败");
  }

  return false;
};

// 地理坐标转像素坐标
const calculateGeoToPixel = async () => {
  if (!currentImage.value || !geoLongitude.value || !geoLatitude.value) {
    showErrorMessage("请填写完整的地理坐标", "操作失败");
    return;
  }

  try {
    // 调用API将地理坐标转换为像素坐标
    const longitude = parseFloat(geoLongitude.value);
    const latitude = parseFloat(geoLatitude.value);

    // 修改为后端期望的格式：包含longitude和latitude字段的对象数组
    const pointsPosition = [{ longitude, latitude }];

    const response = await post(
      `/api/calculate_geo_to_pixel/${currentImage.value.id}`,
      pointsPosition
    );

    if (
      response.data &&
      response.data.status === "success" &&
      response.data.pixel &&
      response.data.pixel.length > 0
    ) {
      const pixel = response.data.pixel[0];
      pixelResult.value = {
        x: Math.round(pixel[0]),
        y: Math.round(pixel[1]),
      };

      // 创建新点显示在画布上
      const newPoint: Point = {
        id: points.value.length + 1, // 临时ID
        pixel_x: pixelResult.value.x,
        pixel_y: pixelResult.value.y,
        name:
          selectedBuildingPoint.value?.name ||
          `地理点(${longitude}, ${latitude})`,
        longitude: longitude.toString(),
        latitude: latitude.toString(),
        image_id: currentImage.value.id,
        building_point_id: selectedBuildingPoint.value?.id || -1,
      };

      points.value = [newPoint]; // 只显示当前点
    } else {
      showErrorMessage("坐标转换失败", "操作失败");
    }
  } catch (error) {
    console.error("地理转像素坐标失败:", error);
    showErrorMessage(`地理转像素坐标失败，请稍后重试，${error}`, "操作失败");
  }
};
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
  width: 350px;
  padding: 15px;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
  gap: 20px; /* 统一间距 */
  flex-shrink: 0; /* 防止面板被压缩 */
  overflow-y: auto;
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

/* 转换区域样式 */
.transformation-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.transformation-section h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-group label {
  font-size: 14px;
  color: #666;
}

/* 结果区域样式 */
.result-section {
  padding: 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.result-section h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.result-item {
  margin-bottom: 5px;
  font-size: 14px;
  color: #333;
}

/* 说明区域样式 */
.instructions {
  padding: 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.instructions p {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.instructions ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #666;
}

.instructions li {
  margin-bottom: 5px;
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
