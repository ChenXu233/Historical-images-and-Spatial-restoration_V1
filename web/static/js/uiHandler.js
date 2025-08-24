// UI事件处理模块

// 坐标验证函数
function validateCoordinate(value) {
  if (!value) return true;
  // 放宽校验规则，允许更多格式的坐标
  const regex = /^-?\d+(\.\d*)?$/;
  return regex.test(value);
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

// 导出函数供其他模块使用
window.validateCoordinate = validateCoordinate;
window.setupEventListeners = setupEventListeners;
window.handleImageUpload = handleImageUpload;
window.handleCSVUpload = handleCSVUpload;
