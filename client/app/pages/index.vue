<template>
  <div class="hero-text">
    <el-card class="bg-white/80 backdrop-blur-sm shadow-lg border-0">
      <template #header>
        <div class="card-header">
          <span class="text-xl font-semibold">历史图像与空间修复</span>
        </div>
      </template>
      <div class="card-body">
        <p class="text-gray-600 mb-4">
          数字化保存和修复历史图像，结合空间信息技术实现历史场景的三维重建与展示，
          让珍贵的历史文化遗产以全新的方式呈现给世人。
        </p>
        <div class="flex gap-4 mt-6 padding-4">
          <router-link to="/labelling">
            <el-button type="primary">开始标注</el-button>
          </router-link>
          <router-link to="/imageUpload">
            <el-button type="primary">上传图像</el-button>
          </router-link>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.header {
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.menu {
  display: flex;
  align-items: center;
}

.menu .el-menu-item {
  font-size: 16px;
  padding: 0 16px;
}

.hero {
  position: relative;
  overflow: hidden;
}

.hero-text {
  z-index: 1;
}

.feature-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.icon-wrapper {
  transition: transform 0.3s ease;
}

.feature-card:hover .icon-wrapper {
  transform: translateY(-5px);
}

.call-to-action {
  position: relative;
  overflow: hidden;
}

.footer {
  color: #fff;
}

.footer a {
  color: #fff;
  text-decoration: none;
}

.footer a:hover {
  color: #409eff;
}
</style>
