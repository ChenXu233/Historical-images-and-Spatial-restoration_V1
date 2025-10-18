<template>
  <div class="min-h-screen bg-gray-100">
    <div class="flex md:flex-row">
      <div ref="canvasContainer" class="canvas-container">
        <canvas id="imageCanvas" ref="imageCanvas" />
        <div id="coordinates" class="coordinates" />
      </div>
      <div class="md:w-1/3 p-6 space-y-6 bg-gray-50">
        <div class="file-upload bg-white p-4 rounded-lg shadow-sm">
          <label
            for="imageLoader"
            class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors cursor-pointer"
            >上传历史照片</label
          >
          <input
            id="imageLoader"
            type="file"
            accept="image/*"
            style="display: none"
            @change="handleImageUpload"
          />
          <span id="fileStatus" class="file-status ml-4 text-gray-600">
            {{ fileStatus }}
          </span>
        </div>

        <div class="file-upload">
          <select
            id="existingImageSelect"
            v-model="selectedImageId"
            class="w-full bg-white border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">选择已有历史照片</option>
            <option v-for="img in images" :key="img.id" :value="img.id">
              {{ img.name }}
            </option>
          </select>
          <button
            class="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors ml-2"
            @click="loadExistingImage"
          >
            加载选中照片
          </button>
        </div>

        <div class="file-upload">
          <label
            for="csvLoader"
            class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors cursor-pointer"
            style="cursor: pointer; width: auto"
            >上传已知坐标</label
          >
          <input
            type="file"
            id="csvLoader"
            accept=".csv,.xlsx"
            style="display: none"
            @change="handleCSVUpload"
          />
          <span id="csvStatus" class="file-status">{{ csvStatus }}</span>
        </div>

        <div class="zoom-controls">
          <label>缩放: </label>
          <input
            type="range"
            id="zoom"
            min="10"
            max="300"
            step="1"
            :value="zoomPercent"
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            @input="handleZoomSliderInput"
          />
          <input
            type="number"
            id="zoomValue"
            class="ml-2 w-16 bg-white border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            min="10"
            max="300"
            :value="zoomPercent"
            @change="handleZoomInputChange"
          />
          <span>%</span>
        </div>

        <div class="input-group">
          <select
            id="buildingPointSelect"
            class="w-full bg-white border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
            v-model="selectedBuildingPoint"
            @change="handleBuildingPointSelect"
          >
            <option value="">选择现有建筑点或输入新数据</option>
            <option
              v-for="point in buildingPoints"
              :key="point.name"
              :value="point.name"
            >
              {{ point.name }} (经度: {{ point.longitude }}, 纬度:
              {{ point.latitude }})
            </option>
          </select>
          <input
            type="text"
            id="longitude"
            placeholder="经度"
            class="w-full bg-white border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
            v-model="longitude"
          />
          <input
            type="text"
            id="latitude"
            placeholder="纬度"
            class="w-full bg-white border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
            v-model="latitude"
          />
          <input
            type="text"
            id="buildName"
            placeholder="建筑名称"
            class="w-full bg-white border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
            v-model="buildName"
          />
          <div class="coordinate-hint text-sm text-gray-500">
            单位为度，小数部分为5位，如199.39048
          </div>
          <button
            @click="saveBuildingPointToDB"
            class="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors mb-2"
          >
            保存建筑点到数据库
          </button>
        </div>

        <button
          @click="saveAnnotations"
          class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors mb-2"
        >
          保存标注
        </button>
        <button
          @click="deleteAnnotations"
          class="w-full bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors mb-2"
        >
          删除标注
        </button>
        <button
          @click="calculateCameraPosition"
          class="w-full bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition-colors"
        >
          计算相机位置
        </button>
      </div>
    </div>
    <div class="point-list p-4 bg-white rounded-lg shadow-sm" id="pointList">
      <div v-if="points.length === 0">
        <p>暂无标注点</p>
      </div>
      <table v-else class="point-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>X坐标</th>
            <th>Y坐标</th>
            <th>建筑名称</th>
            <th>经度</th>
            <th>纬度</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(point, index) in points" :key="index">
            <td>{{ index + 1 }}</td>
            <td>{{ point.x }}</td>
            <td>{{ point.y }}</td>
            <td>{{ point.name || "" }}</td>
            <td>{{ point.longitude || "" }}</td>
            <td>{{ point.latitude || "" }}</td>
            <td>
              <button @click="deletePoint(index)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Toast组件 -->
    <div v-if="showToast" :class="['toast', `toast-${toastType}`]" ref="toast">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { request, get, post } from "../utils/request";
import { config } from "../config/config";

// 导入外部库
import * as XLSX from "xlsx";

// 全局变量
const canvas = ref(null);
const ctx = ref(null);
const canvasContainer = ref(null);
const coordsDisplay = ref(null);
let image = ref(null);
let scale = ref(1);
let offsetX = ref(0);
let offsetY = ref(0);
let isDragging = ref(false);
let lastX = ref(0);
let lastY = ref(0);

// 状态管理
const points = ref([]);
const currentImageName = ref(""); // 当前图片名称
const currentImageId = ref(""); // 当前图片ID
const featurePoints = ref({}); // 存储上传的坐标数据
const fileStatus = ref("未选择照片");
const csvStatus = ref("未选择表格");
const zoomPercent = ref(100);
const images = ref([]);
const selectedImageId = ref("");
const buildingPoints = ref([]);
const selectedBuildingPoint = ref("");
const longitude = ref("");
const latitude = ref("");
const buildName = ref("");

// Toast状态
const showToast = ref(false);
const toastMessage = ref("");
const toastType = ref("info");

// 初始化
onMounted(async () => {
  await nextTick();

  // 初始化画布
  canvas.value = document.getElementById("imageCanvas");
  ctx.value = canvas.value.getContext("2d");
  coordsDisplay.value = document.getElementById("coordinates");

  // 设置事件监听器
  setupEventListeners();

  // 加载建筑点数据
  await loadBuildingPointData();

  // 加载已有图片列表
  await loadExistingImages();
});

// 设置事件监听器
function setupEventListeners() {
  // 画布事件
  canvas.value.addEventListener("mousedown", handleMouseDown);
  canvas.value.addEventListener("mousemove", handleMouseMove);
  canvas.value.addEventListener("mouseup", handleMouseUp);
  canvas.value.addEventListener("wheel", handleWheel);
  canvas.value.addEventListener("contextmenu", (e) => {
    e.preventDefault();
  });

  // 窗口大小变化事件
  window.addEventListener("resize", () => {
    if (image.value) {
      fitImageToCanvas();
    }
  });
}

// 自动调整图像大小以适应画布
function fitImageToCanvas() {
  if (!image.value) return;

  const container = canvasContainer.value;
  const containerWidth = container.clientWidth;
  const containerHeight = container.clientHeight;

  // 计算缩放比例
  const scaleX = containerWidth / image.value.width;
  const scaleY = containerHeight / image.value.height;
  scale.value = Math.min(scaleX, scaleY, 1); // 取最小值，确保图像完全可见

  // 更新画布大小
  canvas.value.width = containerWidth;
  canvas.value.height = containerHeight;

  // 计算偏移量以使图像居中
  offsetX.value = (containerWidth - image.value.width * scale.value) / 2;
  offsetY.value = (containerHeight - image.value.height * scale.value) / 2;

  // 更新缩放控制器的值
  zoomPercent.value = Math.round(scale.value * 100);

  redraw();
}

// 重绘画布
function redraw() {
  ctx.value.clearRect(0, 0, canvas.value.width, canvas.value.height);

  if (image.value) {
    ctx.value.save();
    ctx.value.translate(offsetX.value, offsetY.value);
    ctx.value.scale(scale.value, scale.value);
    ctx.value.drawImage(image.value, 0, 0);

    // 绘制标记点
    points.value.forEach((point) => {
      ctx.value.beginPath();
      ctx.value.arc(point.x, point.y, 3 / scale.value, 0, 2 * Math.PI);
      ctx.value.fillStyle = "red";
      ctx.value.fill();

      ctx.value.font = `${20 / scale.value}px Arial`;
      ctx.value.fillStyle = "yellow";
      ctx.value.fillText(
        point.name,
        point.x + 5 / scale.value,
        point.y + 5 / scale.value
      );
    });

    ctx.value.restore();
  }
}

// 鼠标按下事件处理
function handleMouseDown(e) {
  const rect = canvas.value.getBoundingClientRect();
  // 调整坐标计算方式，考虑画布的缩放和偏移
  const x = (e.clientX - rect.left - offsetX.value) / scale.value;
  const y = (e.clientY - rect.top - offsetY.value) / scale.value;

  if (e.button === 0) {
    // 左键 - 添加点
    if (buildName.value) {
      points.value.push({
        x: x,
        y: y,
        symbol: buildName.value, // 使用建筑名称作为符号
        name: buildName.value,
        longitude: longitude.value,
        latitude: latitude.value,
      });
      redraw();
    } else {
      showToastMsg("请先选择或输入特征点信息", "warning");
    }
  } else if (e.button === 2) {
    // 右键 - 开始拖动
    isDragging.value = true;
    lastX.value = e.clientX;
    lastY.value = e.clientY;
  }
}

// 鼠标移动事件处理
function handleMouseMove(e) {
  const rect = canvas.value.getBoundingClientRect();
  const x = (e.clientX - rect.left - offsetX.value) / scale.value;
  const y = (e.clientY - rect.top - offsetY.value) / scale.value;

  // 更新坐标显示
  if (coordsDisplay.value && image.value) {
    coordsDisplay.value.textContent = `坐标: X=${Math.round(x)}, Y=${Math.round(
      y
    )}`;
  }

  // 处理拖动
  if (isDragging.value) {
    const deltaX = e.clientX - lastX.value;
    const deltaY = e.clientY - lastY.value;
    offsetX.value += deltaX;
    offsetY.value += deltaY;
    lastX.value = e.clientX;
    lastY.value = e.clientY;
    redraw();
  }
}

// 鼠标释放事件处理
function handleMouseUp() {
  isDragging.value = false;
}

// 鼠标滚轮事件处理（缩放）
function handleWheel(e) {
  e.preventDefault();
  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
  const newScale = scale.value * zoomFactor;

  // 限制缩放范围
  if (newScale >= 0.1 && newScale <= 3) {
    scale.value = newScale;
    zoomPercent.value = Math.round(scale.value * 100);
    redraw();
  }
}

// 处理缩放滑块输入
function handleZoomSliderInput(e) {
  const zoomValue = parseInt(e.target.value);
  zoomPercent.value = zoomValue;
  scale.value = zoomValue / 100;
  redraw();
}

// 处理缩放输入框变化
function handleZoomInputChange(e) {
  let zoomValue = parseInt(e.target.value);
  if (isNaN(zoomValue)) zoomValue = 100;
  zoomValue = Math.max(10, Math.min(300, zoomValue));
  zoomPercent.value = zoomValue;
  scale.value = zoomValue / 100;
  redraw();
}

// 处理建筑点选择变化
function handleBuildingPointSelect() {
  if (selectedBuildingPoint.value) {
    const point = buildingPoints.value.find(
      (p) => p.name === selectedBuildingPoint.value
    );
    if (point) {
      buildName.value = point.name;
      longitude.value = point.longitude;
      latitude.value = point.latitude;
    }
  }
}

// 处理图像上传
function handleImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (event) {
    image.value = new Image();
    image.value.onload = function () {
      currentImageName.value = file.name;
      fileStatus.value = currentImageName.value;

      // 清空之前的标注
      points.value = [];

      fitImageToCanvas();

      // 将图片上传到后端
      const formData = new FormData();
      formData.append("image", file);

      request({
        url: "/api/upload_image",
        method: "post",
        data: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })
        .then((response) => {
          console.log("图片上传成功:", response.data);
          currentImageId.value = response.data.id;
          showToastMsg("图片上传成功", "success");
        })
        .catch((error) => {
          console.error("图片上传失败:", error);
          showToastMsg("图片上传失败", "error");
        });
    };
    image.value.src = event.target.result;
  };
  reader.readAsDataURL(file);
}

// 处理CSV上传
function handleCSVUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  csvStatus.value = file.name;

  const reader = new FileReader();
  reader.onload = function (event) {
    const data = new Uint8Array(event.target.result);
    const workbook = XLSX.read(data, { type: "array" });

    // 假设数据在第一个工作表
    const firstSheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[firstSheetName];

    // 转换为JSON
    const jsonData = XLSX.utils.sheet_to_json(worksheet);

    // 处理数据
    featurePoints.value = jsonData;

    // 将数据添加到建筑点选择下拉框
    jsonData.forEach((point) => {
      if (point["建筑名称"] && point["经度"] && point["纬度"]) {
        buildingPoints.value.push({
          name: point["建筑名称"],
          longitude: point["经度"],
          latitude: point["纬度"],
        });
      }
    });

    showToastMsg("坐标数据加载成功", "success");
  };
  reader.readAsArrayBuffer(file);
}

// 加载已有图片列表
async function loadExistingImages() {
  try {
    const response = await get("/api/images");
    images.value = response.data;
  } catch (error) {
    console.error("获取图片列表失败:", error);
    showToastMsg("获取图片列表失败", "error");
  }
}

// 加载选中的已有图片
async function loadExistingImage() {
  if (!selectedImageId.value) {
    showToastMsg("请先选择一张图片", "warning");
    return;
  }

  try {
    const response = await get(`/api/images/${selectedImageId.value}`);
    const data = response.data;

    image.value = new Image();
    image.value.onload = function () {
      currentImageName.value = data.name;
      currentImageId.value = data.id;
      fileStatus.value = currentImageName.value;

      // 清空之前的标注
      points.value = [];

      fitImageToCanvas();
      // 获取该图片的标注信息
      loadAnnotationsForImage(data.id);
    };
    image.value.src = config.apiBaseUrl + data.path;
  } catch (error) {
    console.error("加载图片失败:", error);
    showToastMsg("加载图片失败", "error");
  }
}

// 加载建筑点数据
async function loadBuildingPointData() {
  try {
    const response = await get("/api/building_points");
    buildingPoints.value = response.data;
  } catch (error) {
    console.error("加载建筑点数据失败:", error);
    // 可以选择不显示错误提示，因为这是可选功能
  }
}

// 加载指定图片的标注信息
async function loadAnnotationsForImage(imageId) {
  try {
    const response = await get(`/api/images/${imageId}/features`);
    const data = response.data;

    // 将后端返回的数据转换为前端需要的格式
    points.value = data.map((feature) => ({
      x: feature.x,
      y: feature.y,
      name: feature.name,
      longitude: feature.longitude,
      latitude: feature.latitude,
    }));

    redraw();
  } catch (error) {
    console.error("加载标注信息失败:", error);
  }
}

// 保存建筑点到数据库
async function saveBuildingPointToDB() {
  if (!buildName.value || !longitude.value || !latitude.value) {
    showToastMsg("请填写完整的建筑点信息", "warning");
    return;
  }

  // 验证坐标格式
  if (
    !validateCoordinate(longitude.value) ||
    !validateCoordinate(latitude.value)
  ) {
    showToastMsg("坐标格式不正确", "error");
    return;
  }

  try {
    await post("/api/building_points", {
      name: buildName.value,
      longitude: longitude.value,
      latitude: latitude.value,
    });

    showToastMsg("建筑点保存成功", "success");
    // 重新加载建筑点数据
    await loadBuildingPointData();
  } catch (error) {
    console.error("保存建筑点失败:", error);
    showToastMsg("保存建筑点失败", "error");
  }
}

// 保存标注信息
async function saveAnnotations() {
  if (!currentImageId.value) {
    showToastMsg("请先选择或上传一张图片", "warning");
    return;
  }

  // 准备标注数据
  const features = points.value.map((point) => ({
    x: point.x,
    y: point.y,
    image_id: currentImageId.value,
    name: point.name,
    longitude: point.longitude,
    latitude: point.latitude,
  }));

  try {
    // 批量上传标注点
    const response = await post("/api/upload_features", { features });
    console.log("上传响应:", response.data);
    showToastMsg("标注信息保存成功", "success");
  } catch (error) {
    console.error("保存标注信息失败:", error);
    showToastMsg("保存标注信息失败", "error");
  }
}

// 删除标注信息
async function deleteAnnotations() {
  if (!currentImageId.value) {
    showToastMsg("请先选择一张图片", "warning");
    return;
  }

  if (confirm("确定要删除这张图片的所有标注信息吗？")) {
    try {
      await request({
        url: `/api/images/${currentImageId.value}/features`,
        method: "delete",
      });

      // 清空前端数据
      points.value = [];
      showToastMsg("标注信息已删除", "success");
    } catch (error) {
      console.error("删除标注信息失败:", error);
      showToastMsg("删除标注信息失败", "error");
    }
  }
}

// 删除单个点
function deletePoint(index) {
  points.value.splice(index, 1);
  redraw();
}

// 计算相机位置
async function calculateCameraPosition() {
  if (points.value.length < 3) {
    showToastMsg("至少需要3个标注点才能计算相机位置", "warning");
    return;
  }

  try {
    const response = await post("/api/calculate_camera_position", {
      image_id: currentImageId.value,
      points: points.value,
    });

    showToastMsg(
      `相机位置计算成功: 经度=${response.data.longitude}, 纬度=${response.data.latitude}, 高度=${response.data.altitude}`,
      "success"
    );
  } catch (error) {
    console.error("计算相机位置失败:", error);
    showToastMsg("计算相机位置失败", "error");
  }
}

// 坐标验证函数
function validateCoordinate(value) {
  if (!value) return true;
  // 放宽校验规则，允许更多格式的坐标
  const regex = /^-?\d+(\.\d*)?$/;
  return regex.test(value);
}

// 显示Toast消息
function showToastMsg(message, type = "info") {
  showToast.value = true;
  toastMessage.value = message;
  toastType.value = type;

  // 3秒后自动隐藏
  setTimeout(() => {
    showToast.value = false;
  }, 3000);
}

// 清理事件监听器
onUnmounted(() => {
  if (canvas.value) {
    canvas.value.removeEventListener("mousedown", handleMouseDown);
    canvas.value.removeEventListener("mousemove", handleMouseMove);
    canvas.value.removeEventListener("mouseup", handleMouseUp);
    canvas.value.removeEventListener("wheel", handleWheel);
  }

  window.removeEventListener("resize", () => {
    if (image.value) {
      fitImageToCanvas();
    }
  });
});
</script>

<style scoped>
.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background-color: #f0f0f0;
}

#imageCanvas {
  display: block;
}

.coordinates {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 14px;
}

.point-table {
  width: 100%;
  border-collapse: collapse;
}

.point-table th,
.point-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.point-table th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.point-table tr:nth-child(even) {
  background-color: #f9f9f9;
}

/* Toast 样式 */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 4px;
  color: white;
  font-size: 14px;
  z-index: 10000;
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
  animation: fadeIn 0.3s forwards;
}

@keyframes fadeIn {
  to {
    opacity: 1;
  }
}

.toast-success {
  background-color: #4caf50;
}

.toast-error {
  background-color: #f44336;
}

.toast-warning {
  background-color: #ff9800;
}

.toast-info {
  background-color: #2196f3;
}
</style>
