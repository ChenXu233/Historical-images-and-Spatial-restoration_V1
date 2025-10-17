// 数据上传和下载模块

// 上传标注信息到后端
function uploadAnnotations() {
  if (!currentImageId) {
    console.log("没有选中图片，无法上传标注信息");
    return;
  }

  // 准备标注数据
  const features = points.map((point) => {
    const feature = {
      x: point.x,
      y: point.y,
      image_id: currentImageId,
      name: point.name,
      longitude: point.longitude,
      latitude: point.latitude,
    };
    return feature;
  });

  console.log("准备上传标注信息:", features);

  // 批量上传标注点
  const uploadData = {
    features: features,
  };

  fetch("/api/upload_features", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(uploadData),
  })
    .then((response) => {
      if (response.ok) {
        console.log("标注点上传成功");
        return response.json();
      } else {
        console.error("标注点上传失败");
        return response.text().then((text) => {
          throw new Error(text);
        });
      }
    })
    .then((data) => {
      console.log("上传响应:", data);
      showToast("标注信息上传成功", "success");
    })
    .catch((error) => {
      console.error("上传过程中发生错误:", error);
      showToast("上传过程中发生错误: " + error.message, "error");
    });
}

// 页面加载时获取已有图片列表
function loadExistingImages() {
  fetch("/api/images")
    .then((response) => response.json())
    .then((data) => {
      const select = document.getElementById("existingImageSelect");
      select.innerHTML = '<option value="">选择已有历史照片</option>';
      data.forEach((image) => {
        const option = document.createElement("option");
        option.value = image.id;
        option.textContent = image.name;
        select.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("获取图片列表失败:", error);
      showToast("获取图片列表失败", "error");
    });
}

// 加载选中的已有图片
function loadExistingImage() {
  const select = document.getElementById("existingImageSelect");
  const imageId = select.value;

  if (!imageId) {
    showToast("请先选择一张图片", "warning");
    return;
  }

  fetch(`/api/images/${imageId}`)
    .then((response) => response.json())
    .then((data) => {
      image = new Image();
      image.onload = function () {
        currentImageName = data.name;
        currentImageId = data.id; // 保存图片ID到全局变量
        fitImageToCanvas();
        // 获取该图片的标注信息
        loadAnnotationsForImage(imageId);
        updatePointList();
        document.getElementById("fileStatus").textContent = currentImageName;
      };
      image.src = data.path;
      console.log("加载图片:", data.path);
    })
    .catch((error) => {
      console.error("加载图片失败:", error);
      showToast("加载图片失败", "error");
    });
}

// 加载图片的标注信息
function loadAnnotationsForImage(imageId) {
  fetch(`/api/images/${imageId}/features`)
    .then((response) => response.json())
    .then((data) => {
      console.log("从后端获取的标注数据:", data);
      points = data.map((feature) => ({
        id: feature.id,
        x: feature.pixel_x,
        y: feature.pixel_y,
        image_id: currentImageId,
        name: feature.name || "未命名点",
        longitude: feature.longitude || "",
        latitude: feature.latitude || "",
      }));
      console.log("处理后的points数组:", points);
      annotations[currentImageName] = points;
      updatePointList();
      redraw(); // 确保在加载数据后重绘
    })
    .catch((error) => {
      console.error("加载标注信息失败:", error);
      showToast("加载标注信息失败", "error");
    });
}

// 从后端获取建筑点数据并填充到下拉菜单
function loadBuildingPointData() {
  fetch("/api/building_points")
    .then((response) => response.json())
    .then((data) => {
      const select = document.getElementById("buildingPointSelect");
      select.innerHTML = '<option value="">选择现有建筑点或输入新数据</option>';
      data.forEach((point) => {
        const option = document.createElement("option");
        option.value = point.id;
        option.textContent = `${point.name} (经度: ${point.longitude}, 纬度: ${point.latitude})`;
        select.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("获取建筑点数据失败:", error);
      showToast("获取建筑点数据失败", "error");
    });
}

// 保存建筑点到数据库
function saveBuildingPointToDB() {
  const name = document.getElementById("buildName").value;
  const longitude = document.getElementById("longitude").value;
  const latitude = document.getElementById("latitude").value;

  if (!name || !longitude || !latitude) {
    showToast("请填写完整的建筑点信息", "warning");
    return;
  }

  // 验证坐标格式
  if (!validateCoordinate(longitude) || !validateCoordinate(latitude)) {
    showToast("坐标格式不正确，请输入有效的数字", "warning");
    return;
  }

  const buildingPointData = {
    name: name,
    longitude: parseFloat(longitude),
    latitude: parseFloat(latitude),
  };

  fetch("/api/upload_building_point", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildingPointData),
  })
    .then((response) => {
      if (response.ok) {
        showToast("建筑点保存成功", "success");
        // 重新加载建筑点数据
        loadBuildingPointData();
        // 清空输入框
        document.getElementById("buildName").value = "";
        document.getElementById("longitude").value = "";
        document.getElementById("latitude").value = "";
      } else {
        showToast("建筑点保存失败", "error");
      }
    })
    .catch((error) => {
      console.error("保存过程中发生错误:", error);
      showToast("保存过程中发生错误", "error");
    });
}

// 计算相机位置
function calculateCameraPosition() {
  if (!currentImageId) {
    showToast("请先选择一张图片", "warning");
    return;
  }

  // 发送请求到后端计算相机位置
  fetch("/api/calculate_camera_position", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `image_id=${currentImageId}`,
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      } else {
        return response.text().then((text) => {
          throw new Error(text);
        });
      }
    })
    .then((data) => {
      console.log("相机位置计算结果:", data);
      // 显示确认弹窗
      const cameraPosition = `X: ${data.camera_position[0]}, Y: ${data.camera_position[1]}， Z: ${data.camera_position[2]}`;

      if (confirm(`相机位置计算成功:\n${cameraPosition}\n${data.message}\n`)) {
        console.log("用户确认了相机位置");
        // 用户点击确定后的操作可以在这里添加
      } else {
        console.log("用户取消了相机位置");
        // 用户点击取消后的操作可以在这里添加
      }
    })
    .catch((error) => {
      console.error("计算过程中发生错误:", error);
      showToast("计算过程中发生错误: " + error.message, "error");
    });
}

// 导出函数供其他模块使用
window.uploadAnnotations = uploadAnnotations;
window.loadExistingImages = loadExistingImages;
window.loadExistingImage = loadExistingImage;
window.loadAnnotationsForImage = loadAnnotationsForImage;
window.loadBuildingPointData = loadBuildingPointData;
window.saveBuildingPointToDB = saveBuildingPointToDB;
window.calculateCameraPosition = calculateCameraPosition;
