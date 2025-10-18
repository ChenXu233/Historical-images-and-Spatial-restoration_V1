<template>
  <div class="canvas-container" ref="canvasContainer">
    <canvas
      ref="canvas"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseLeave"
      @contextmenu.prevent
      @wheel.prevent="handleWheel"
    ></canvas>
    <!-- 图片加载指示器 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">{{ loadingText }}</div>
    </div>
    <div class="coordinates" v-if="showCoordinates">{{ coordinates }}</div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  onMounted,
  onUnmounted,
  nextTick,
  watch,
  defineProps,
  defineEmits,
} from "vue";
import type { Point, Image } from "../utils/types";
import { config } from "../config/config";
import { get } from "../utils/request";

// Props
const props = defineProps<{
  image: Image | null;
  points: Point[];
  showCoordinates?: boolean;
}>();

// Emits
const emit = defineEmits<{
  pointAdded: [point: Point];
  pointsLoaded: [points: Point[]];
}>();

// 状态管理
const canvas = ref<HTMLCanvasElement | null>(null);
const canvasContainer = ref<HTMLDivElement | null>(null);
const ctx = ref<CanvasRenderingContext2D | null>(null);
const scale = ref(1);
const offsetX = ref(0);
const offsetY = ref(0);
const isRightMouseDown = ref(false);
const lastX = ref(0);
const lastY = ref(0);
const coordinates = ref("X: 0, Y: 0");
const isLoading = ref(false);
const loadingText = ref("");
const isCanvasInitialized = ref(false);

// 图片缓存
const imageCache = new Map<string, HTMLImageElement>();
const loadedImage = ref<HTMLImageElement | null>(null);

// 初始化画布
async function initializeCanvas() {
  if (!canvas.value || isCanvasInitialized.value) return;

  try {
    ctx.value = canvas.value.getContext("2d");
    setCanvasSize();
    isCanvasInitialized.value = true;

    // 如果有图片，立即加载
    if (props.image) {
      await loadImageAndFeatures(props.image);
    }
  } catch (error) {
    console.error("初始化画布失败:", error);
  }
}

// 清理画布资源
function cleanup() {
  if (canvas.value) {
    ctx.value = null;
    isCanvasInitialized.value = false;
  }
}

// 设置画布大小
function setCanvasSize() {
  if (!canvas.value || !canvasContainer.value) return;

  const containerWidth = canvasContainer.value.clientWidth;
  const containerHeight = canvasContainer.value.clientHeight;

  canvas.value.width = containerWidth;
  canvas.value.height = containerHeight;
}

// 绘制图片和标注点
function drawCanvas(imageElement: HTMLImageElement, points: Point[]) {
  if (!canvas.value || !ctx.value) return;

  try {
    // 清空画布
    ctx.value.clearRect(0, 0, canvas.value.width, canvas.value.height);

    // 如果没有图片，直接返回
    if (!imageElement) return;

    ctx.value.save();
    ctx.value.translate(offsetX.value, offsetY.value);
    ctx.value.scale(scale.value, scale.value);

    // 绘制图像
    ctx.value.drawImage(imageElement, 0, 0);

    // 绘制标记点
    points.forEach((point) => {
      if (!ctx.value) return;

      ctx.value.beginPath();
      ctx.value.arc(
        point.pixel_x,
        point.pixel_y,
        3 / scale.value,
        0,
        2 * Math.PI
      );
      ctx.value.fillStyle = "red";
      ctx.value.fill();

      ctx.value.font = `${12 / scale.value}px Arial`;
      ctx.value.fillStyle = "yellow";
      ctx.value.fillText(
        point.name,
        point.pixel_x + 5 / scale.value,
        point.pixel_y + 5 / scale.value
      );
    });
  } catch (error) {
    console.error("重绘画布时出错:", error);
  } finally {
    ctx.value?.restore();
  }
}

// 调整图片以适应画布
function adjustImageToCanvas(imageElement: HTMLImageElement) {
  if (!canvas.value || !canvasContainer.value || !imageElement) return;

  setCanvasSize();

  const containerWidth = canvasContainer.value.clientWidth;
  const containerHeight = canvasContainer.value.clientHeight;

  // 计算缩放比例 - 确保图片完全可见
  const scaleX = containerWidth / imageElement.width;
  const scaleY = containerHeight / imageElement.height;
  scale.value = Math.min(scaleX, scaleY, 1);

  // 计算偏移量以使图像居中
  offsetX.value = (containerWidth - imageElement.width * scale.value) / 2;
  offsetY.value = (containerHeight - imageElement.height * scale.value) / 2;
}

// 图片加载器 - 处理图片加载、缓存和错误处理
async function loadImage(item: Image): Promise<HTMLImageElement> {
  // 检查缓存中是否已有该图片
  const cacheKey = `${item.id}_${item.path}`;
  if (imageCache.has(cacheKey)) {
    console.log("使用缓存的图片:", item.name);
    return imageCache.get(cacheKey)!;
  }

  // 创建新的图片对象
  const img = new Image();

  // 设置跨域支持
  img.crossOrigin = "anonymous";

  // 确保图片路径正确构建
  let imageUrl = item.path;
  // 如果路径不是以http开头，则添加apiBaseUrl
  if (!imageUrl.startsWith("http") && config.apiBaseUrl) {
    // 确保路径格式正确（处理斜杠问题）
    const baseUrl = config.apiBaseUrl.endsWith("/")
      ? config.apiBaseUrl.slice(0, -1)
      : config.apiBaseUrl;
    const path = imageUrl.startsWith("/") ? imageUrl : `/${imageUrl}`;
    imageUrl = `${baseUrl}${path}`;
  }

  console.log("构建的图片URL:", imageUrl);
  console.log("使用的apiBaseUrl:", config.apiBaseUrl);

  // 返回Promise以便更好地处理异步加载
  return new Promise((resolve, reject) => {
    // 设置加载超时（10秒）
    const timeoutId = setTimeout(() => {
      reject(new Error("图片加载超时"));
    }, 10000);

    img.onload = () => {
      clearTimeout(timeoutId);
      console.log(
        "图片加载成功:",
        item.name,
        "尺寸:",
        img.width,
        "x",
        img.height
      );
      // 存入缓存
      imageCache.set(cacheKey, img);
      resolve(img);
    };

    img.onerror = (event) => {
      clearTimeout(timeoutId);
      console.error(
        "图片加载失败:",
        item.name,
        "URL:",
        imageUrl,
        "错误:",
        event
      );
      reject(new Error(`加载图片失败: ${item.name}`));
    };

    // 开始加载图片
    try {
      img.src = imageUrl;
      // 如果图片已经在缓存中（浏览器缓存）
      if (img.complete) {
        clearTimeout(timeoutId);
        imageCache.set(cacheKey, img);
        resolve(img);
      }
    } catch (error) {
      clearTimeout(timeoutId);
      reject(error);
    }
  });
}

// 加载图片和特征点
async function loadImageAndFeatures(imageItem: Image) {
  if (!isCanvasInitialized.value) return;

  isLoading.value = true;
  loadingText.value = `正在加载: ${imageItem.name}`;

  try {
    // 重置状态
    scale.value = 1;
    offsetX.value = 0;
    offsetY.value = 0;

    // 加载图片（带重试逻辑）
    let retryCount = 0;
    const maxRetries = 2;

    while (retryCount <= maxRetries) {
      try {
        loadedImage.value = await loadImage(imageItem);
        break; // 加载成功，跳出循环
      } catch (error) {
        retryCount++;
        if (retryCount > maxRetries) {
          throw error; // 超过重试次数，抛出错误
        }
        console.warn(
          `图片加载失败，正在重试 (${retryCount}/${maxRetries}):`,
          error
        );
        // 等待一段时间后重试
        await new Promise((resolve) => setTimeout(resolve, 1000 * retryCount));
      }
    }

    if (!loadedImage.value) {
      throw new Error("图片加载失败");
    }

    // 调整图片以适应画布
    adjustImageToCanvas(loadedImage.value);

    // 加载特征点数据
    try {
      const response = await get(`/api/images/${imageItem.id}/features`);
      const features = response.data;

      // 将后端返回的特征点转换为前端的Point格式
      const points: Point[] = features.map((feature: any) => ({
        id: feature.id,
        pixel_x: feature.pixel_x,
        pixel_y: feature.pixel_y,
        name: feature.name,
        longitude: feature.longitude?.toString() || "",
        latitude: feature.latitude?.toString() || "",
      }));

      // 触发特征点加载完成事件
      emit("pointsLoaded", points);
    } catch (error) {
      console.log("获取特征点失败，使用空列表", error);
      // 触发空特征点加载完成事件
      emit("pointsLoaded", []);
    }
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "加载图片失败，请稍后重试";
    console.error("加载图片错误:", error);
    loadingText.value = `加载失败: ${imageItem.name}`;
  } finally {
    isLoading.value = false;
  }
}

// 计算鼠标在图像上的实际坐标
function calculateImageCoordinates(event: MouseEvent): {
  x: number;
  y: number;
} {
  if (!canvas.value || !loadedImage.value) {
    return { x: 0, y: 0 };
  }

  const rect = canvas.value.getBoundingClientRect();
  const x = Math.round(
    (event.clientX - rect.left - offsetX.value) / scale.value
  );
  const y = Math.round(
    (event.clientY - rect.top - offsetY.value) / scale.value
  );
  return { x, y };
}

// 鼠标事件处理
function handleMouseDown(event: MouseEvent) {
  if (!canvas.value || !loadedImage.value || !isCanvasInitialized.value) return;

  if (event.button === 2 || event.button === 1) {
    // 右键按下或中键按下
    isRightMouseDown.value = true;
    lastX.value = event.clientX;
    lastY.value = event.clientY;
    canvas.value.style.cursor = "grabbing";
    return;
  }

  if (event.button === 0) {
    // 左键添加点
    const { x, y } = calculateImageCoordinates(event);

    // 创建新点并触发事件
    const newPoint: Point = {
      pixel_x: x,
      pixel_y: y,
      name: `Point`,
      longitude: "",
      latitude: "",
    };

    emit("pointAdded", newPoint);
  }
}

function handleMouseMove(event: MouseEvent) {
  if (!canvas.value || !loadedImage.value || !isCanvasInitialized.value) return;

  const { x, y } = calculateImageCoordinates(event);
  coordinates.value = `X: ${x}, Y: ${y}`;

  if (isRightMouseDown.value) {
    offsetX.value += event.clientX - lastX.value;
    offsetY.value += event.clientY - lastY.value;
    lastX.value = event.clientX;
    lastY.value = event.clientY;

    // 直接重绘画布
    if (loadedImage.value) {
      drawCanvas(loadedImage.value, props.points);
    }
  }
}

function handleMouseUp(event: MouseEvent) {
  if (!canvas.value) return;

  if (event.button === 2) {
    // 右键释放
    isRightMouseDown.value = false;
    canvas.value.style.cursor = "crosshair";
  }
}

function handleMouseLeave() {
  if (!canvas.value) return;

  isRightMouseDown.value = false;
  canvas.value.style.cursor = "crosshair";
}

// 鼠标滚轮缩放处理
function handleWheel(event: WheelEvent) {
  // 只有在有图片和canvas已初始化时才处理缩放
  if (!canvas.value || !loadedImage.value || !isCanvasInitialized.value) return;

  const zoomFactor = 1.1;
  const rect = canvas.value.getBoundingClientRect();
  const mousePos = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };

  // 计算当前鼠标位置在缩放前的坐标
  const prevMousePos = {
    x: (mousePos.x - offsetX.value) / scale.value,
    y: (mousePos.y - offsetY.value) / scale.value,
  };

  if (event.deltaY < 0) {
    // 缩小
    scale.value = Math.min(scale.value * zoomFactor, 3);
  } else {
    // 放大
    scale.value = Math.max(scale.value / zoomFactor, 0.1);
  }

  // 更新偏移量以使缩放以鼠标位置为中心
  offsetX.value = mousePos.x - prevMousePos.x * scale.value;
  offsetY.value = mousePos.y - prevMousePos.y * scale.value;

  // 直接重绘画布
  if (loadedImage.value) {
    drawCanvas(loadedImage.value, props.points);
  }
}

// 窗口大小改变处理
function handleResize() {
  // 如果有图片，调整图片以适应画布
  if (loadedImage.value && isCanvasInitialized.value && canvas.value) {
    adjustImageToCanvas(loadedImage.value);
    // 直接重绘画布
    drawCanvas(loadedImage.value, props.points);
  } else if (isCanvasInitialized.value && canvas.value) {
    // 如果没有图片，仅设置画布大小
    setCanvasSize();
  }
}

// 监听图片变化
watch(
  () => props.image,
  (newImage) => {
    if (newImage && isCanvasInitialized.value) {
      loadImageAndFeatures(newImage);
    }
  }
);

// 监听特征点变化，自动重绘
watch(
  () => props.points,
  () => {
    if (loadedImage.value && isCanvasInitialized.value) {
      drawCanvas(loadedImage.value, props.points);
    }
  }
);

// 生命周期钩子
onMounted(() => {
  nextTick(() => {
    initializeCanvas();
    window.addEventListener("resize", handleResize);
  });
});

onUnmounted(() => {
  cleanup();
  window.removeEventListener("resize", handleResize);
});
</script>

<style scoped>
.canvas-container {
  position: relative;
  border: 1px solid #ccc;
  width: 100%;
  height: 100%;
  overflow: hidden;
  min-width: 0; /* 防止canvas溢出 */
}

canvas {
  cursor: crosshair;
}

.coordinates {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px;
  border-radius: 4px;
  pointer-events: none;
}

/* 图片加载指示器样式 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}

.loading-text {
  color: white;
  margin-top: 10px;
  font-size: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
