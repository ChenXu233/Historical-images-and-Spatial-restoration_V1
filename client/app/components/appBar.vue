<template>
  <el-header class="app-bar">
    <el-menu
      :default-active="currentRoute"
      class="app-menu"
      mode="horizontal"
      background-color="#304156"
      text-color="#fff"
      active-text-color="#ffd04b"
      @select="handleMenuSelect"
    >
      <el-menu-item index="/">
        <span>首页</span>
      </el-menu-item>
      <el-menu-item index="/imageUpload">
        <span>图片上传</span>
      </el-menu-item>
      <el-menu-item index="/buildingPoints">
        <span>建筑点地理坐标管理</span>
      </el-menu-item>
      <el-menu-item index="/labelling">
        <span>图片标注</span>
      </el-menu-item>
      <el-menu-item index="/coordinateTransformation">
        <span>图像与地理坐标转换</span>
      </el-menu-item>
    </el-menu>
  </el-header>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const currentRoute = ref("/");

onMounted(() => {
  // 设置当前路由为默认激活项
  currentRoute.value = router.currentRoute.value.path;
});

const handleMenuSelect = (index: string) => {
  // 处理菜单选择事件，跳转到对应的路由
  router.push(index);
};
</script>

<style scoped>
.app-bar {
  padding: 0;
  height: 60px;
  display: flex;
  align-items: center;
}

.app-menu {
  width: 100%;
  height: 60px;
}

:deep(.el-menu--horizontal > .el-menu-item) {
  height: 60px;
  line-height: 60px;
}
</style>
