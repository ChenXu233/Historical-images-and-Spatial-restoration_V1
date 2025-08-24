// 主初始化文件

// 初始化
document.addEventListener("DOMContentLoaded", function () {
  console.log("页面加载完成，初始化...");
  setupEventListeners();
  // 页面加载时自动加载建筑点数据
  loadBuildingPointData();

  // 页面加载时获取已有图片列表
  loadExistingImages();
});
