<template>
  <div class="building-points-container">
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>建筑坐标点管理</span>
        </div>
      </template>

      <!-- 建筑点上传区域 -->
      <el-row :gutter="20" class="mb-4">
        <el-col :span="12">
          <el-card title="添加单个建筑点">
            <el-form
              ref="singlePointForm"
              :model="singlePointForm"
              label-width="120px"
            >
              <el-form-item label="建筑点名称" prop="name">
                <el-input
                  v-model="singlePointForm.name"
                  placeholder="请输入建筑点名称"
                />
              </el-form-item>
              <el-form-item label="纬度" prop="latitude">
                <el-input
                  v-model.number="singlePointForm.latitude"
                  placeholder="请输入纬度"
                />
              </el-form-item>
              <el-form-item label="经度" prop="longitude">
                <el-input
                  v-model.number="singlePointForm.longitude"
                  placeholder="请输入经度"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleSinglePointUpload"
                  >上传建筑点</el-button
                >
                <el-button @click="resetSinglePointForm">重置</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card title="批量上传建筑点">
            <el-upload
              ref="batchUploadRef"
              action="#"
              :auto-upload="false"
              :before-upload="handleBeforeUpload"
              :on-change="handleFileChange"
              :show-file-list="false"
            >
              <el-button type="primary" plain>选择JSON文件</el-button>
              <div v-if="selectedFile" class="file-info mt-2">
                已选择文件: {{ selectedFile.name }}
                <el-button type="text" size="small" @click="clearFile"
                  >清除</el-button
                >
              </div>
            </el-upload>
            <el-button
              type="success"
              class="mt-4"
              @click="handleBatchUpload"
              :disabled="!selectedFile"
            >
              开始批量上传
            </el-button>
          </el-card>
        </el-col>
      </el-row>

      <!-- 建筑点列表和搜索 -->
      <div class="search-container mb-4">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索建筑点名称"
          style="width: 300px"
          prefix-icon="Search"
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" class="ml-2" @click="handleSearch"
          >搜索</el-button
        >
        <el-button @click="clearSearch">清除搜索</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredBuildingPoints"
        style="width: 100%"
        border
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="建筑点名称" min-width="180" />
        <el-table-column prop="latitude" label="纬度" width="180" />
        <el-table-column prop="longitude" label="经度" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleViewOnMap(scope.row)"
            >
              查看位置
            </el-button>
            <el-button
              type="warning"
              size="small"
              @click="handleEdit(scope.row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredBuildingPoints.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 地图查看弹窗 -->
    <el-dialog
      v-model="mapDialogVisible"
      title="建筑点地图位置"
      width="80%"
      :before-close="handleMapDialogClose"
    >
      <div class="map-container">
        <div id="map" class="map"></div>
        <div class="map-info">
          <h4>建筑点信息</h4>
          <p>名称: {{ selectedPoint?.name }}</p>
          <p>纬度: {{ selectedPoint?.latitude }}</p>
          <p>经度: {{ selectedPoint?.longitude }}</p>
        </div>
      </div>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑建筑点"
      width="50%"
      :before-close="handleEditDialogClose"
    >
      <el-form ref="editPointForm" :model="editPointForm" label-width="120px">
        <el-form-item label="建筑点名称" prop="name">
          <el-input
            v-model="editPointForm.name"
            placeholder="请输入建筑点名称"
          />
        </el-form-item>
        <el-form-item label="纬度" prop="latitude">
          <el-input
            v-model.number="editPointForm.latitude"
            placeholder="请输入纬度"
          />
        </el-form-item>
        <el-form-item label="经度" prop="longitude">
          <el-input
            v-model.number="editPointForm.longitude"
            placeholder="请输入经度"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpdate">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed, watch } from "vue";
import { get, post, put, del } from "../utils/request";
// Local UploadFile type (subset compatible with Element Plus UploadFile)
type UploadFile = {
  name: string;
  size?: number;
  type?: string;
  uid?: string | number;
  status?: string;
  response?: any;
  raw?: File | Blob;
  percentage?: number;
};

// 类型定义
interface BuildingPoint {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

// 建筑点列表
const buildingPoints = ref<BuildingPoint[]>([]);
// 加载状态
const loading = ref(false);
// 搜索关键字
const searchKeyword = ref("");
// 分页数据
const currentPage = ref(1);
const pageSize = ref(10);
// 单个上传表单数据
const singlePointForm = reactive<{
  name: string;
  latitude: number;
  longitude: number;
}>({
  name: "",
  latitude: 0,
  longitude: 0,
});
// 地图弹窗相关
const mapDialogVisible = ref(false);
const selectedPoint = ref<BuildingPoint | null>(null);
// 编辑弹窗相关
const editDialogVisible = ref(false);
const editPointForm = reactive<{
  id: number | null;
  name: string;
  latitude: number;
  longitude: number;
}>({
  id: null,
  name: "",
  latitude: 0,
  longitude: 0,
});
// 批量上传相关
const selectedFile = ref<UploadFile | null>(null);
const batchUploadRef = ref<any>(null);

// 获取建筑点列表
const fetchBuildingPoints = async () => {
  try {
    loading.value = true;
    const response = await get<BuildingPoint[]>("/api/building_points");
    buildingPoints.value = response.data;
  } catch (error) {
    console.error("获取建筑点列表失败:", error);
  } finally {
    loading.value = false;
  }
};

// 处理单个建筑点上传
const handleSinglePointUpload = async () => {
  try {
    const response = await post<{
      status: string;
      message: string;
    }>("/api/upload_building_point", singlePointForm);
    if (response.data.status === "success") {
      ElMessage.success(response.data.message);
      resetSinglePointForm();
      fetchBuildingPoints();
    } else {
      ElMessage.warning(response.data.message);
    }
  } catch (error) {
    console.error("上传建筑点失败:", error);
  }
};

// 重置单个上传表单
const resetSinglePointForm = () => {
  singlePointForm.name = "";
  singlePointForm.latitude = 0;
  singlePointForm.longitude = 0;
};

// 处理文件上传前的校验
const handleBeforeUpload = (file: UploadFile) => {
  const isJSON = file.name.endsWith(".json");
  if (!isJSON) {
    ElMessage.error("只能上传JSON文件!");
  }
  return isJSON;
};

// 处理文件选择变化
const handleFileChange = (file: UploadFile) => {
  selectedFile.value = file;
};

// 清除选择的文件
const clearFile = () => {
  selectedFile.value = null;
  if (batchUploadRef.value) {
    batchUploadRef.value.clearFiles();
  }
};

// 处理批量上传
const handleBatchUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning("请先选择文件");
    return;
  }

  try {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const content = e.target?.result as string;
        const data = JSON.parse(content);

        // 检查数据格式
        if (!data.points || !Array.isArray(data.points)) {
          ElMessage.error("文件格式错误，需要包含points数组");
          return;
        }

        const response = await post<{
          status: string;
          message: string;
        }>("/api/upload_building_points", data);
        ElMessage.success(response.data.message);
        clearFile();
        fetchBuildingPoints();
      } catch (error) {
        ElMessage.error("文件解析失败，请检查文件格式");
      }
    };
    reader.readAsText(selectedFile.value.raw as Blob);
  } catch (error) {
    console.error("批量上传失败:", error);
  }
};

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1;
};

// 清除搜索
const clearSearch = () => {
  searchKeyword.value = "";
  currentPage.value = 1;
};

// 根据搜索关键字过滤建筑点
const filteredBuildingPoints = computed(() => {
  if (!searchKeyword.value) {
    return buildingPoints.value;
  }
  return buildingPoints.value.filter((point) =>
    point.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  );
});

// 分页后的建筑点列表
const paginatedBuildingPoints = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredBuildingPoints.value.slice(start, end);
});

// 处理分页大小变化
const handleSizeChange = (size: number) => {
  pageSize.value = size;
};

// 处理当前页码变化
const handleCurrentChange = (current: number) => {
  currentPage.value = current;
};

// 处理地图查看
const handleViewOnMap = (point: BuildingPoint) => {
  selectedPoint.value = point;
  mapDialogVisible.value = true;
};

// 处理地图弹窗关闭
const handleMapDialogClose = () => {
  mapDialogVisible.value = false;
};

// 处理编辑
const handleEdit = (point: BuildingPoint) => {
  editPointForm.id = point.id;
  editPointForm.name = point.name;
  editPointForm.latitude = point.latitude;
  editPointForm.longitude = point.longitude;
  editDialogVisible.value = true;
};

// 处理编辑弹窗关闭
const handleEditDialogClose = () => {
  editDialogVisible.value = false;
};

// 处理更新
const handleUpdate = async () => {
  if (!editPointForm.id) {
    return;
  }

  try {
    const response = await put<{
      status: string;
      message: string;
    }>(`/api/building_points/${editPointForm.id}`, {
      name: editPointForm.name,
      latitude: editPointForm.latitude,
      longitude: editPointForm.longitude,
    });

    if (response.data.status === "success") {
      ElMessage.success(response.data.message);
      editDialogVisible.value = false;
      fetchBuildingPoints();
    }
  } catch (error) {
    console.error("更新建筑点失败:", error);
  }
};

// 处理删除
const handleDelete = async (pointId: number) => {
  try {
    await ElMessageBox.confirm(
      "确定要删除这个建筑点吗？删除后相关的特征点也会被删除。",
      "删除确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    const response = await del<{
      status: string;
      message: string;
    }>(`/api/building_points/${pointId}`);
    if (response.data.status === "success") {
      ElMessage.success(response.data.message);
      fetchBuildingPoints();
    }
  } catch (error) {
    // 用户取消删除
  }
};

// 初始化地图
const initMap = () => {
  // 这里可以根据项目需要集成地图API，例如百度地图、高德地图等
  // 简单的地图模拟实现
  const mapElement = document.getElementById("map");
  if (mapElement && selectedPoint.value) {
    // 清空地图内容
    mapElement.innerHTML = "";

    // 创建一个简单的地图模拟
    const mapWidth = mapElement.clientWidth;
    const mapHeight = mapElement.clientHeight;

    // 绘制简单的地图背景
    const mapBackground = document.createElement("div");
    mapBackground.style.width = "100%";
    mapBackground.style.height = "100%";
    mapBackground.style.backgroundColor = "#e6f7ff";
    mapBackground.style.border = "1px solid #91d5ff";
    mapBackground.style.position = "relative";
    mapBackground.style.borderRadius = "4px";

    // 绘制网格线
    for (let i = 0; i <= 10; i++) {
      const horizontalLine = document.createElement("div");
      horizontalLine.style.position = "absolute";
      horizontalLine.style.height = "1px";
      horizontalLine.style.width = "100%";
      horizontalLine.style.top = `${i * 10}%`;
      horizontalLine.style.backgroundColor = "rgba(145, 213, 255, 0.3)";
      mapBackground.appendChild(horizontalLine);
    }

    for (let i = 0; i <= 10; i++) {
      const verticalLine = document.createElement("div");
      verticalLine.style.position = "absolute";
      verticalLine.style.width = "1px";
      verticalLine.style.height = "100%";
      verticalLine.style.left = `${i * 10}%`;
      verticalLine.style.backgroundColor = "rgba(145, 213, 255, 0.3)";
      mapBackground.appendChild(verticalLine);
    }

    // 计算点的位置（这里是简单的模拟计算）
    // 实际项目中应该使用地图API的坐标转换函数
    const centerLat = 30.0;
    const centerLng = 120.0;
    const scale = 100; // 缩放比例

    const x =
      (selectedPoint.value.longitude - centerLng) * scale + mapWidth / 2;
    const y =
      mapHeight / 2 - (selectedPoint.value.latitude - centerLat) * scale;

    // 创建标记点
    const marker = document.createElement("div");
    marker.style.position = "absolute";
    marker.style.width = "20px";
    marker.style.height = "20px";
    marker.style.backgroundColor = "#ff4d4f";
    marker.style.borderRadius = "50%";
    marker.style.left = `${Math.max(0, Math.min(x - 10, mapWidth - 20))}px`;
    marker.style.top = `${Math.max(0, Math.min(y - 10, mapHeight - 20))}px`;
    marker.style.cursor = "pointer";
    marker.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.15)";

    // 创建标记点的文字标签
    const label = document.createElement("div");
    label.style.position = "absolute";
    label.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
    label.style.color = "white";
    label.style.padding = "2px 6px";
    label.style.borderRadius = "4px";
    label.style.fontSize = "12px";
    label.style.whiteSpace = "nowrap";
    label.style.left = "25px";
    label.style.top = "-5px";
    label.textContent = selectedPoint.value.name;
    marker.appendChild(label);

    mapBackground.appendChild(marker);
    mapElement.appendChild(mapBackground);
  }
};

// 监听地图弹窗显示事件
watch(
  () => mapDialogVisible.value,
  (newValue) => {
    if (newValue) {
      // 延迟初始化地图，确保DOM已经渲染
      setTimeout(() => {
        initMap();
      }, 100);
    }
  }
);

// 页面加载时获取建筑点列表
onMounted(() => {
  fetchBuildingPoints();
});
</script>

<style scoped>
.building-points-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-container {
  display: flex;
  align-items: center;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
}

.map-container {
  display: flex;
  height: 500px;
}

.map {
  flex: 1;
  margin-right: 20px;
}

.map-info {
  width: 200px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .map-container {
    flex-direction: column;
  }

  .map {
    margin-right: 0;
    margin-bottom: 20px;
    height: 300px;
  }

  .map-info {
    width: 100%;
  }
}
</style>
