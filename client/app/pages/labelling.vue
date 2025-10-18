<template>
  <div class="container">
    <div class="canvas-container-wrapper" ref="canvasContainerWrapper">
      <CanvasViewer
        :image="currentImage"
        :show-coordinates="true"
        :points="points"
        @pointAdded="handlePointAdded"
        @pointsLoaded="handlePointsLoaded"
      />
    </div>
    <div class="control-panel">
      <div class="image-selector-container">
        <label class="input-label">选择历史照片</label>
        <el-autocomplete
          v-model="currentImageName"
          :fetch-suggestions="queryImages"
          placeholder="请输入关键词搜索照片"
          :trigger-on-focus="false"
          @select="handleImageSelectByAutocomplete"
          class="w-full"
          name-property="name"
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
        </el-autocomplete>
        <div class="status-text">{{ imageStatusText }}</div>
      </div>

      <CoordinateInput
        v-model:pointName="pointName"
        v-model:longitude="longitude"
        v-model:latitude="latitude"
      />

      <button class="input-field" @click="async () => await saveAnnotations()">
        保存标注
      </button>
      <PointList :points="points" @removePoint="removePoint" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { showErrorMessage, get, post } from "../utils/request";
import type { Point, Image } from "../utils/types";

// 导入组件
import CoordinateInput from "../components/CoordinateInput.vue";
import PointList from "../components/PointList.vue";
import CanvasViewer from "../components/CanvasViewer.vue";

// 状态管理
const points = ref<Point[]>([]);
const currentImage = ref<Image | null>(null);
const allImages = ref<Image[]>([]);
const isLoadingImages = ref(false);
const imageStatusText = ref("未选择照片");
const currentImageName = ref("");
const canvasContainerWrapper = ref<HTMLDivElement | null>(null);

// 表单输入
const pointName = ref("");
const longitude = ref("");
const latitude = ref("");

// 页面加载完成后立即尝试获取图片列表
onMounted(async () => {
  // 获取图片列表
  await refreshImages();
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

// 搜索图片
function queryImages(query: string, callback: (data: any[]) => void) {
  if (!query) {
    // 如果没有搜索词，不显示任何结果
    callback([]);
    return;
  }

  const results = allImages.value
    .filter((image) => image.name.toLowerCase().includes(query.toLowerCase()))
    .map((image) => ({
      value: image.name,
      ...image,
    }));

  callback(results);
}

// 通过Autocomplete选择图片处理
async function handleImageSelectByAutocomplete(item: Image) {
  currentImage.value = item;
  currentImageName.value = item.name;
  imageStatusText.value = item.name;
}

// 处理特征点加载完成事件
function handlePointsLoaded(newPoints: Point[]) {
  points.value = newPoints;
}

// 处理添加新点事件
function handlePointAdded(newPoint: Point) {
  const name = pointName.value || `Point ${points.value.length + 1}`;

  // 创建新点，合并表单输入的坐标信息
  const pointToAdd: Point = {
    ...newPoint,
    name,
    longitude: longitude.value,
    latitude: latitude.value,
  };

  points.value.push(pointToAdd);

  // 清空输入框
  pointName.value = "";
  longitude.value = "";
  latitude.value = "";
}

// 删除点
function removePoint(index: number) {
  points.value.splice(index, 1);
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
        image_id: currentImageName.value,
        name: point.name,
        longitude: point.longitude ? parseFloat(point.longitude) : undefined,
        latitude: point.latitude ? parseFloat(point.latitude) : undefined,
      })),
    };

    // 发送到后端保存
    await post("/api/upload_features", featuresData);

    showErrorMessage("标注信息已保存", "保存成功", "info");
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
  height: calc(100vh - 40px);
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
