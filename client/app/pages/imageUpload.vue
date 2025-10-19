<template>
  <div class="container">
    <!-- 页面标题 -->
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span class="text-xl font-semibold">图片上传与管理</span>
        </div>
      </template>

      <!-- 图片上传区域 -->
      <div class="upload-section">
        <el-upload
          class="upload-demo"
          drag
          :action="uploadUrl"
          :on-success="handleUploadSuccess"
          :before-upload="beforeUpload"
          :on-error="handleUploadError"
          multiple
          :file-list="uploadFileList"
          :headers="uploadHeaders"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
          <div class="el-upload__tip" slot="tip">
            支持jpg/jpeg/png格式，单个文件不超过10MB
          </div>
        </el-upload>
      </div>
    </el-card>

    <!-- 已上传图片管理区域 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="font-medium">已上传图片</span>
        </div>
      </template>

      <!-- 搜索和操作区域 -->
      <div class="search-section mb-4">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索图片名称"
          class="search-input"
          prefix-icon="el-icon-search"
          @keyup.enter.native="handleSearch"
        >
          <template #append>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
        <el-button type="default" @click="resetSearch" class="ml-2"
          >重置</el-button
        >
      </div>

      <!-- 图片列表 -->
      <div class="image-list">
        <div v-if="loading" class="loading-container">
          <el-loading
            v-loading="loading"
            element-loading-text="加载中..."
            fullscreen
          ></el-loading>
        </div>

        <el-empty
          v-else-if="images.length === 0"
          description="暂无图片"
        ></el-empty>

        <div v-else class="image-grid">
          <el-card
            v-for="image in images"
            :key="image.id"
            class="image-card"
            :body-style="{ padding: '12px' }"
          >
            <div class="image-preview">
              <img
                :src="getImageUrl(image.path)"
                :alt="image.name"
                class="preview-image"
              />
              <div class="image-overlay" @click="previewImage(image)">
                <i class="el-icon-zoom-in text-white"></i>
              </div>
            </div>
            <div class="image-info mt-2">
              <p class="image-name truncate">{{ image.name }}</p>
              <div class="image-actions">
                <el-button type="text" size="small" @click="previewImage(image)"
                  >查看</el-button
                >
                <el-button
                  type="text"
                  size="small"
                  danger
                  @click="confirmDelete(image.id)"
                  >删除</el-button
                >
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="images.length > 0" class="pagination-section mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 36, 48]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalImages"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 图片预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="图片预览" :width="'80%'">
      <img :src="previewImageUrl" alt="预览图片" class="preview-full-image" />
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 删除确认对话框 -->
    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="30%">
      <span>确定要删除这张图片吗？删除后将无法恢复。</span>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleDelete">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { get, del } from "../utils/request";
import { type Image } from "../utils/types";
import { config } from "../config/config";

// 上传相关配置
const uploadUrl = `${config.apiBaseUrl}/api/upload_image`;
const uploadHeaders = { "Content-Type": "multipart/form-data" };
const uploadFileList = ref<any[]>([]);

// 图片列表相关状态
const images = ref<any[]>([]);
const totalImages = ref(0);
const currentPage = ref(1);
const pageSize = ref(12);
const loading = ref(false);
const searchKeyword = ref("");

// 对话框相关状态
const previewDialogVisible = ref(false);
const previewImageUrl = ref("");
const deleteDialogVisible = ref(false);
const imageToDelete = ref<number | null>(null);

// 计算图片URL
const getImageUrl = (path: string) => {
  return `${config.apiBaseUrl}${path}`;
};

// 上传前的校验
const beforeUpload = (file: File) => {
  const isValidType = /\.(jpg|jpeg|png)$/i.test(file.name);
  if (!isValidType) {
    ElMessage.error("只支持jpg/jpeg/png格式的图片");
    return false;
  }

  const isLt10M = file.size / 1024 / 1024 < 10;
  if (!isLt10M) {
    ElMessage.error("图片大小不能超过10MB");
    return false;
  }

  return true;
};

// 上传成功回调
const handleUploadSuccess = async (response: any, uploadFile: any) => {
  ElMessage.success("图片上传成功");
  // 重新加载图片列表
  await fetchImages();
};

// 上传失败回调
const handleUploadError = (error: any) => {
  ElMessage.error("图片上传失败，请稍后重试");
};

// 获取图片列表
const fetchImages = async () => {
  loading.value = true;
  try {
    let url = `/api/images`;
    if (searchKeyword.value.trim()) {
      // 实际项目中，应该在后端实现搜索功能
      // 这里为了演示，我们在前端过滤
    }

    const response = await get<Image[]>(url);
    const allImages = response.data;

    // 前端过滤搜索结果
    let filteredImages = allImages;
    if (searchKeyword.value.trim()) {
      const keyword = searchKeyword.value.toLowerCase();
      filteredImages = allImages.filter((img: any) =>
        img.name.toLowerCase().includes(keyword)
      );
    }

    // 分页处理
    totalImages.value = filteredImages.length;
    const startIndex = (currentPage.value - 1) * pageSize.value;
    const endIndex = startIndex + pageSize.value;
    images.value = filteredImages.slice(startIndex, endIndex);
  } catch (error) {
    console.error("获取图片列表失败:", error);
  } finally {
    loading.value = false;
  }
};

// 搜索图片
const handleSearch = () => {
  currentPage.value = 1;
  fetchImages();
};

// 重置搜索
const resetSearch = () => {
  searchKeyword.value = "";
  currentPage.value = 1;
  fetchImages();
};

// 分页大小改变
const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchImages();
};

// 当前页码改变
const handleCurrentChange = (current: number) => {
  currentPage.value = current;
  fetchImages();
};

// 预览图片
const previewImage = (image: any) => {
  previewImageUrl.value = getImageUrl(image.path);
  previewDialogVisible.value = true;
};

// 确认删除
const confirmDelete = (id: number) => {
  imageToDelete.value = id;
  deleteDialogVisible.value = true;
};

// 执行删除
const handleDelete = async () => {
  if (!imageToDelete.value) return;

  try {
    await del(`/api/images/${imageToDelete.value}`);
    ElMessage.success("图片删除成功");
    deleteDialogVisible.value = false;
    // 重新加载图片列表
    await fetchImages();
  } catch (error) {
    console.error("删除图片失败:", error);
  }
};

// 初始加载图片列表
onMounted(() => {
  fetchImages();
});
</script>

<style scoped>
.container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.upload-section {
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
}

.search-section {
  display: flex;
  align-items: center;
}

.search-input {
  width: 300px;
}

.image-list {
  margin-top: 10px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.image-preview {
  position: relative;
  width: 100%;
  height: 150px;
  overflow: hidden;
  border-radius: 4px;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
  cursor: pointer;
}

.image-preview:hover .image-overlay {
  opacity: 1;
}

.image-preview:hover .preview-image {
  transform: scale(1.1);
}

.image-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.image-name {
  margin: 0;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.pagination-section {
  display: flex;
  justify-content: flex-end;
}

.preview-full-image {
  width: 100%;
  height: auto;
  max-height: 70vh;
  object-fit: contain;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-container {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
