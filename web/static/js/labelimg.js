// 全局变量
const canvas = document.getElementById("imageCanvas");
const ctx = canvas.getContext("2d");
const coordsDisplay = document.getElementById("coordinates");
let points = [];
let image = null;
let scale = 1;
let offsetX = 0;
let offsetY = 0;
let isDragging = false;
let lastX = 0;
let lastY = 0;
let annotations = {}; // 存储所有图片的标注信息
let currentImageName = ""; // 当前图片名称
let currentImageId = ""; // 当前图片ID
let featurePoints = {}; // 存储上传的坐标数据
let isRightMouseDown = false;

// 自动调整图像大小以适应画布
function fitImageToCanvas() {
  if (!image) return;

  const container = canvas.parentElement;
  const containerWidth = container.clientWidth;
  const containerHeight = container.clientHeight;

  // 计算缩放比例
  const scaleX = containerWidth / image.width;
  const scaleY = containerHeight / image.height;
  scale = Math.min(scaleX, scaleY, 1); // 取最小值，确保图像完全可见

  // 更新画布大小
  canvas.width = containerWidth;
  canvas.height = containerHeight;

  // 计算偏移量以使图像居中
  offsetX = (containerWidth - image.width * scale) / 2;
  offsetY = (containerHeight - image.height * scale) / 2;

  // 更新缩放控制器的值
  const zoomPercent = Math.round(scale * 100);
  document.getElementById("zoom").value = zoomPercent;
  document.getElementById("zoomValue").value = zoomPercent;

  redraw();
}

// 坐标验证函数
function validateCoordinate(value) {
  if (!value) return true;
  // 放宽校验规则，允许更多格式的坐标
  const regex = /^-?\d+(\.\d*)?$/;
  return regex.test(value);
}

// 重绘画布
function redraw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (image) {
    ctx.save();
    console.log("绘图参数:", { offsetX, offsetY, scale });
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);
    ctx.drawImage(image, 0, 0);

    // 绘制标记点
    points.forEach((point, index) => {
      console.log("绘制点:", { x: point.x, y: point.y, symbol: point.symbol });
      ctx.beginPath();
      ctx.arc(point.x, point.y, 3 / scale, 0, 2 * Math.PI);
      ctx.fillStyle = "red";
      ctx.fill();

      ctx.font = `${12 / scale}px Arial`;
      ctx.fillStyle = "yellow";
      ctx.fillText(point.symbol, point.x + 5 / scale, point.y + 5 / scale);
    });

    ctx.restore();
  }
}

// 更新点列表显示
function updatePointList() {
  const pointListDiv = document.getElementById("pointList");
  pointListDiv.innerHTML = "";

  if (points.length === 0) {
    pointListDiv.innerHTML = "<p>暂无标注点</p>";
    return;
  }

  // 创建表格来显示点列表
  const table = document.createElement("table");
  table.className = "point-table";

  // 创建表头
  const headerRow = table.insertRow();
  const headers = [
    "序号",
    "X坐标",
    "Y坐标",
    "建筑名称",
    "符号",
    "经度",
    "纬度",
    "操作",
  ];
  headers.forEach((headerText) => {
    const th = document.createElement("th");
    th.textContent = headerText;
    headerRow.appendChild(th);
  });

  // 添加点数据
  points.forEach((point, index) => {
    const row = table.insertRow();
    const cells = [
      index + 1,
      point.x,
      point.y,
      point.name || "",
      point.symbol || "",
      point.longitude || "",
      point.latitude || "",
    ];

    cells.forEach((cellText) => {
      const cell = row.insertCell();
      cell.textContent = cellText;
      cell.className = "point-table-cell";
    });

    // 添加删除按钮
    const actionCell = row.insertCell();
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "删除";
    deleteButton.onclick = () => removePoint(index);
    actionCell.appendChild(deleteButton);
    actionCell.className = "point-table-cell";
  });

  pointListDiv.appendChild(table);
}

// 删除点
function removePoint(index) {
  points.splice(index, 1);
  updatePointList();
  redraw();
}

// 保存标注信息
function saveAnnotations() {
  if (currentImageName) {
    annotations[currentImageName] = points;

    // 上传标注信息到后端
    uploadAnnotations();

    alert("标注信息已保存");
  }
}

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
      image_id: parseInt(currentImageId),
      name: point.name || "未命名点",
      symbol: point.symbol || "",
    };

    // 如果有建筑点ID，则添加该字段
    if (point.building_point_id) {
      feature.building_point_id = parseInt(point.building_point_id);
    } else {
      // 如果没有建筑点ID，则从输入框获取建筑点信息
      feature.longitude =
        parseFloat(document.getElementById("longitude").value) || null;
      feature.latitude =
        parseFloat(document.getElementById("latitude").value) || null;
      feature.name = document.getElementById("buildName").value || feature.name;
    }

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
      alert("标注信息上传成功");
    })
    .catch((error) => {
      console.error("上传过程中发生错误:", error);
      alert("上传过程中发生错误: " + error.message);
    });
}

// 删除标注信息
function deleteAnnotations() {
  if (!currentImageId) {
    alert("请先选择一张图片");
    return;
  }

  if (confirm("确定要删除这张图片的所有标注信息吗？")) {
    // 发送请求到后端删除标注信息
    fetch(`/api/images/${currentImageId}/features`, {
      method: "DELETE",
    })
      .then((response) => {
        if (response.ok) {
          // 清空前端数据
          points = [];
          annotations[currentImageName] = [];
          updatePointList();
          redraw();
          alert("标注信息已删除");
        } else {
          alert("删除标注信息失败");
        }
      })
      .catch((error) => {
        console.error("删除过程中发生错误:", error);
        alert("删除过程中发生错误");
      });
  }
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
      alert("获取图片列表失败");
    });
}

// 加载选中的已有图片
function loadExistingImage() {
  const select = document.getElementById("existingImageSelect");
  const imageId = select.value;

  if (!imageId) {
    alert("请先选择一张图片");
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
      alert("加载图片失败");
    });
}

// 加载图片的标注信息
function loadAnnotationsForImage(imageId) {
  fetch(`/api/images/${imageId}/features`)
    .then((response) => response.json())
    .then((data) => {
      console.log("从后端获取的标注数据:", data);
      points = data.map((feature) => ({
        x: feature.pixel_x,
        y: feature.pixel_y,
        image_id: currentImageId,
        // 为保持前端显示功能正常，添加默认值
        name: feature.name || "未命名点",
        symbol: feature.label || "199",
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
      alert("加载标注信息失败");
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
      alert("获取建筑点数据失败");
    });
}

// 保存建筑点到数据库
function saveBuildingPointToDB() {
  const name = document.getElementById("buildName").value;
  const longitude = document.getElementById("longitude").value;
  const latitude = document.getElementById("latitude").value;

  if (!name || !longitude || !latitude) {
    alert("请填写完整的建筑点信息");
    return;
  }

  // 验证坐标格式
  if (!validateCoordinate(longitude) || !validateCoordinate(latitude)) {
    alert("坐标格式不正确，请输入有效的数字");
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
        alert("建筑点保存成功");
        // 重新加载建筑点数据
        loadBuildingPointData();
        // 清空输入框
        document.getElementById("buildName").value = "";
        document.getElementById("longitude").value = "";
        document.getElementById("latitude").value = "";
      } else {
        alert("建筑点保存失败");
      }
    })
    .catch((error) => {
      console.error("保存过程中发生错误:", error);
      alert("保存过程中发生错误");
    });
}

// 设置事件监听器
function setupEventListeners() {
  // 图像加载器
  const imageLoader = document.getElementById("imageLoader");
  imageLoader.addEventListener("change", handleImageUpload);

  // CSV加载器
  const csvLoader = document.getElementById("csvLoader");
  csvLoader.addEventListener("change", handleCSVUpload);

  // 缩放控制器
  const zoomSlider = document.getElementById("zoom");
  const zoomInput = document.getElementById("zoomValue");

  zoomSlider.addEventListener("input", function () {
    const zoomPercent = parseInt(this.value);
    zoomInput.value = zoomPercent;
    scale = zoomPercent / 100;
    redraw();
  });

  zoomInput.addEventListener("change", function () {
    let zoomPercent = parseInt(this.value);
    if (isNaN(zoomPercent)) zoomPercent = 100;
    zoomPercent = Math.max(10, Math.min(300, zoomPercent));
    this.value = zoomPercent;
    zoomSlider.value = zoomPercent;
    scale = zoomPercent / 100;
    redraw();
  });

  // 画布事件
  canvas.addEventListener("mousedown", handleMouseDown);
  canvas.addEventListener("mousemove", handleMouseMove);
  canvas.addEventListener("mouseup", handleMouseUp);
  canvas.addEventListener("wheel", handleWheel);
  canvas.addEventListener("contextmenu", function (e) {
    e.preventDefault();
  });

  // 建筑点选择
  const buildingPointSelect = document.getElementById("buildingPointSelect");
  buildingPointSelect.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    if (selectedOption.value) {
      // 从选项文本中提取建筑名称和经纬度
      const text = selectedOption.textContent;
      const name = text.split(" (")[0];
      const coords = text.match(/经度: ([0-9.]+), 纬度: ([0-9.]+)/);

      if (coords) {
        document.getElementById("buildName").value = name;
        document.getElementById("longitude").value = coords[1];
        document.getElementById("latitude").value = coords[2];
      }
    }
  });
}

// 处理图像上传
function handleImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (event) {
    image = new Image();
    image.onload = function () {
      currentImageName = file.name;
      fitImageToCanvas();
      updatePointList();
      document.getElementById("fileStatus").textContent = currentImageName;
    };
    image.src = event.target.result;
  };
  reader.readAsDataURL(file);
}

// 处理CSV上传
function handleCSVUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (event) {
    const csvData = event.target.result;
    Papa.parse(csvData, {
      header: true,
      skipEmptyLines: true,
      complete: function (results) {
        featurePoints = {};
        results.data.forEach((row) => {
          const key = `${row.Symbol}-${row.Name}`;
          featurePoints[key] = {
            Objectid: row.Objectid,
            symbol: row.Symbol,
            name: row.Name,
            height: row.Height,
            longitude: row.Longitude,
            latitude: row.Latitude,
            elevation: row.Elevation,
          };
        });
        document.getElementById(
          "csvStatus"
        ).textContent = `已加载 ${results.data.length} 行数据`;
      },
      error: function (error) {
        console.error("CSV解析错误:", error);
        alert("CSV文件解析失败");
      },
    });
  };
  reader.readAsText(file);
}

// 鼠标事件处理函数
function handleMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left - offsetX) / scale;
  const y = (e.clientY - rect.top - offsetY) / scale;

  if (e.button === 0) {
    // 左键
    // 添加点
    const symbol = document.getElementById("pointSymbol").value;
    const name = document.getElementById("buildName").value;
    const longitude = document.getElementById("longitude").value;
    const latitude = document.getElementById("latitude").value;

    if (symbol && name) {
      points.push({
        x: x,
        y: y,
        symbol: symbol,
        name: name,
        longitude: longitude,
        latitude: latitude,
      });
      updatePointList();
      redraw();
    } else {
      alert("请先选择或输入特征点信息");
    }
  } else if (e.button === 2) {
    // 右键
    isDragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    canvas.style.cursor = "grabbing";
  }
}

function handleMouseMove(e) {
  if (isDragging) {
    const deltaX = e.clientX - lastX;
    const deltaY = e.clientY - lastY;
    offsetX += deltaX;
    offsetY += deltaY;
    lastX = e.clientX;
    lastY = e.clientY;
    redraw();
  }

  // 显示坐标
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left - offsetX) / scale;
  const y = (e.clientY - rect.top - offsetY) / scale;
  coordsDisplay.textContent = `坐标: (${x.toFixed(2)}, ${y.toFixed(2)})`;
}

function handleMouseUp(e) {
  if (e.button === 2) {
    // 右键释放
    isDragging = false;
    canvas.style.cursor = "crosshair";
  }
}

function handleWheel(e) {
  e.preventDefault();
  const zoomIntensity = 0.1;
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const wheel = e.deltaY < 0 ? 1 : -1;
  const zoom = Math.exp(wheel * zoomIntensity);

  // 更新缩放中心点
  offsetX = mouseX - zoom * (mouseX - offsetX);
  offsetY = mouseY - zoom * (mouseY - offsetY);

  // 更新缩放比例
  scale *= zoom;
  scale = Math.max(0.1, Math.min(scale, 3)); // 限制缩放范围

  // 更新UI
  const zoomPercent = Math.round(scale * 100);
  document.getElementById("zoom").value = zoomPercent;
  document.getElementById("zoomValue").value = zoomPercent;

  redraw();
}

// 初始化
document.addEventListener("DOMContentLoaded", function () {
  console.log("页面加载完成，初始化...");
  setupEventListeners();
  // 页面加载时自动加载建筑点数据
  loadBuildingPointData();

  // 页面加载时获取已有图片列表
  loadExistingImages();
});
