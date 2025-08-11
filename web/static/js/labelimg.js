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
  const regex = /^-?\\d+(\\.\\d{0,5})?$/;
  return regex.test(value);
}

// 重绘画布
function redraw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (image) {
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);
    ctx.drawImage(image, 0, 0);

    // 绘制标记点
    points.forEach((point, index) => {
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
  const list = document.getElementById("pointList");
  list.innerHTML = points
    .map(
      (point, index) => `
        <div class="point-item" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                ${point.symbol} - ${point.name} (${point.x}, ${point.y})<br>
                ${point.longitude ? "经度: " + point.longitude + "° " : ""}
                ${point.latitude ? "纬度: " + point.latitude + "° " : ""}
            </div>
            <button onclick="removePoint(${index})" style="margin-left: 10px;">删除</button>
        </div>
    `
    )
    .join("");
}

// 更新已标注图片列表
function updateImageList() {
  const list = document.getElementById("imageList");
  list.innerHTML = Object.keys(annotations)
    .map(
      (imageName) => `
        <div class="image-item" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                ${imageName} (${annotations[imageName].length} 个特征点）
            </div>
            <button onclick="removeAnnotation('${imageName}')" style="margin-left: 10px;">删除</button>
        </div>
    `
    )
    .join("");
}

// 删除点
function removePoint(index) {
  points.splice(index, 1);
  updatePointList();
  redraw();
}

// 删除已保存的标注
function removeAnnotation(imageName) {
  delete annotations[imageName];
  updateImageList();
  if (currentImageName === imageName) {
    points = [];
    updatePointList();
    redraw();
  }
}

// 保存标注信息
function saveAnnotations() {
  if (currentImageName) {
    annotations[currentImageName] = points;
    updateImageList();
    alert("标注信息已保存");
  }
}

// CSV文件处理相关函数
async function exportCSV() {
  console.log("Starting exportCSV...");

  let csvContent = "\\uFEFF"; // 使用BOM标记解决中文乱码问题

  const originalColumns = [
    "Objectid",
    "Symbol",
    "Name",
    "Height",
    "Longitude",
    "Latitude",
    "Elevation",
  ];
  csvContent += originalColumns.join(",") + ",";

  const allImageNames = Object.keys(annotations);
  console.log("All image names:", allImageNames);

  allImageNames.forEach((imageName) => {
    csvContent += `Pixel_x_${imageName},Pixel_y_${imageName},`;
  });
  csvContent += "\\n";

  const allPoints = {};

  allImageNames.forEach((imageName) => {
    const points = annotations[imageName];
    points.forEach((point) => {
      const key = `${point.symbol}-${point.name}`;
      if (!allPoints[key]) {
        allPoints[key] = {};
      }
      allPoints[key][imageName] = point;
    });
  });

  for (const [key, fp] of Object.entries(featurePoints)) {
    if (!fp) continue;

    const [symbol, name] = key.split("-");
    const Objectid = fp.Objectid || "";
    const height = fp.height || "";
    const longitude = fp.longitude || "";
    const latitude = fp.latitude || "";
    const elevation = fp.elevation || "";

    csvContent += `${Objectid},${symbol},${name},${height},${longitude},${latitude},${elevation},`;

    for (const imageName of allImageNames) {
      const point =
        allPoints[key] && allPoints[key][imageName]
          ? allPoints[key][imageName]
          : { x: 0, y: 0 };
      csvContent += `${point.x},${point.y},`;
    }

    csvContent += "\\n";
  }

  downloadCSV(csvContent, "feature_points_with_annotations.csv");
}

function downloadCSV(content, filename) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// 导出带有标注点的照片
async function exportAnnotatedImage() {
  if (!image) {
    alert("请先上传历史照片");
    return;
  }

  const A4Width = 2480; // 210mm * (300 / 25.4)
  const A4Height = 3508; // 297mm * (300 / 25.4)
  const pointRadius = (1.2 * 300) / 25.4;
  const fontSize = 36 * 1.333;

  const imgAspectRatio = image.naturalWidth / image.naturalHeight;
  let imgWidth = A4Width;
  let imgHeight = A4Width / imgAspectRatio;

  if (imgHeight > A4Height) {
    imgHeight = A4Height;
    imgWidth = A4Height * imgAspectRatio;
  }

  const tempCanvas = document.createElement("canvas");
  const tempCtx = tempCanvas.getContext("2d");

  tempCanvas.width = imgWidth;
  tempCanvas.height = imgHeight;

  tempCtx.drawImage(image, 0, 0, imgWidth, imgHeight);

  points.forEach((point) => {
    const x = (point.x * imgWidth) / image.naturalWidth;
    const y = (point.y * imgHeight) / image.naturalHeight;

    tempCtx.beginPath();
    tempCtx.arc(x, y, pointRadius, 0, 2 * Math.PI);
    tempCtx.fillStyle = "red";
    tempCtx.fill();

    tempCtx.font = `${fontSize}px Arial`;
    tempCtx.fillStyle = "yellow";
    tempCtx.fillText(point.symbol, x + 20, y + 10);
  });

  const dataURL = tempCanvas.toDataURL("image/jpeg");
  const link = document.createElement("a");
  link.href = dataURL;
  link.download = "annotated_image.jpg";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// 事件监听器设置
function setupEventListeners() {
  // 图像加载
  document
    .getElementById("imageLoader")
    .addEventListener("change", function (e) {
      const reader = new FileReader();
      reader.onload = function (event) {
        image = new Image();
        image.onload = function () {
          currentImageName = e.target.files[0].name;
          points = annotations[currentImageName] || [];
          fitImageToCanvas();
          updatePointList();
          updateImageList();
          document.getElementById("fileStatus").textContent = currentImageName;
        };
        image.src = event.target.result;
      };
      reader.readAsDataURL(e.target.files[0]);
    });

  // CSV文件加载
  document.getElementById("csvLoader").addEventListener("change", function (e) {
    const file = e.target.files[0];
    const fileName = file.name;
    const fileExtension = fileName.split(".").pop().toLowerCase();

    if (fileExtension === "csv") {
      handleCSVFile(file);
    } else if (fileExtension === "xlsx") {
      handleXLSXFile(file);
    } else {
      alert("Unsupported file format. Please upload a CSV or XLSX file.");
    }
  });

  // 缩放控制
  document.getElementById("zoom").addEventListener("input", function (e) {
    const value = parseInt(e.target.value);
    scale = value / 100;
    document.getElementById("zoomValue").value = value;
    redraw();
  });

  // 手动输入缩放值
  document.getElementById("zoomValue").addEventListener("change", function (e) {
    let value = parseInt(e.target.value);
    value = Math.min(Math.max(value, 10), 300);
    scale = value / 100;
    document.getElementById("zoom").value = value;
    this.value = value;
    redraw();
  });

  // 坐标输入验证
  ["longitude", "latitude"].forEach((id) => {
    document.getElementById(id).addEventListener("input", function (e) {
      if (!validateCoordinate(e.target.value)) {
        e.target.style.backgroundColor = "#ffe6e6";
      } else {
        e.target.style.backgroundColor = "";
      }
    });
  });

  // Canvas事件
  setupCanvasEvents();

  // 窗口大小改变事件
  window.addEventListener("resize", fitImageToCanvas);
}

function setupCanvasEvents() {
  canvas.addEventListener("mousedown", handleCanvasMouseDown);
  canvas.addEventListener("mousemove", handleCanvasMouseMove);
  canvas.addEventListener("mouseup", handleCanvasMouseUp);
  canvas.addEventListener("mouseleave", handleCanvasMouseLeave);
  canvas.addEventListener("wheel", handleCanvasWheel);
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
}

function handleCanvasMouseDown(e) {
  if (e.button === 2) {
    handleRightMouseDown(e);
  } else if (e.button === 0) {
    handleLeftMouseDown(e);
  }
}

function handleRightMouseDown(e) {
  isRightMouseDown = true;
  lastX = e.clientX;
  lastY = e.clientY;
  canvas.style.cursor = "grabbing";
}

function handleLeftMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left - offsetX) / scale;
  const y = (e.clientY - rect.top - offsetY) / scale;

  addNewPoint(x, y);
}

function addNewPoint(x, y) {
  const name =
    document.getElementById("pointName").value ||
    "Point " + (points.length + 1);
  const symbol = document.getElementById("pointSymbol").value || "199";
  const longitude = document.getElementById("longitude").value;
  const latitude = document.getElementById("latitude").value;

  if (
    (longitude && !validateCoordinate(longitude)) ||
    (latitude && !validateCoordinate(latitude))
  ) {
    alert("坐标格式错误！请确保输入正确的十进制度格式，小数点后5位");
    return;
  }

  points.push({
    x: Math.round(x),
    y: Math.round(y),
    name: name,
    symbol: symbol,
    longitude: longitude,
    latitude: latitude,
  });

  clearInputFields();
  updatePointList();
  redraw();
}

function clearInputFields() {
  ["pointName", "pointSymbol", "longitude", "latitude"].forEach((id) => {
    document.getElementById(id).value = "";
  });
}

function handleCanvasMouseMove(e) {
  updateCoordinatesDisplay(e);
  if (isRightMouseDown) {
    handlePanning(e);
  }
}

function updateCoordinatesDisplay(e) {
  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left - offsetX) / scale);
  const y = Math.round((e.clientY - rect.top - offsetY) / scale);
  coordsDisplay.textContent = `X: ${x}, Y: ${y}`;
}

function handlePanning(e) {
  offsetX += e.clientX - lastX;
  offsetY += e.clientY - lastY;
  lastX = e.clientX;
  lastY = e.clientY;
  redraw();
}

function handleCanvasMouseUp(e) {
  if (e.button === 2) {
    isRightMouseDown = false;
    canvas.style.cursor = "crosshair";
  }
}

function handleCanvasMouseLeave() {
  isRightMouseDown = false;
  canvas.style.cursor = "crosshair";
}

function handleCanvasWheel(e) {
  e.preventDefault();
  const zoomFactor = 1.1;
  const mousePos = {
    x: e.clientX - canvas.getBoundingClientRect().left,
    y: e.clientY - canvas.getBoundingClientRect().top,
  };

  const prevMousePos = {
    x: (mousePos.x - offsetX) / scale,
    y: (mousePos.y - offsetY) / scale,
  };

  if (e.deltaY < 0) {
    scale = Math.min(scale * zoomFactor, 3);
  } else {
    scale = Math.max(scale / zoomFactor, 0.1);
  }

  offsetX = mousePos.x - prevMousePos.x * scale;
  offsetY = mousePos.y - prevMousePos.y * scale;

  const zoomPercent = Math.round(scale * 100);
  document.getElementById("zoom").value = zoomPercent;
  document.getElementById("zoomValue").value = zoomPercent;

  redraw();
}

function handleCSVFile(file) {
  Papa.parse(file, {
    header: true,
    dynamicTyping: true,
    complete: function (results) {
      console.log("CSV parse complete:", results.data);
      processFeaturePoints(results.data);
      document.getElementById("csvStatus").textContent = file.name;
    },
  });
}

function handleXLSXFile(file) {
  const reader = new FileReader();
  reader.onload = function (event) {
    const data = new Uint8Array(event.target.result);
    const workbook = XLSX.read(data, { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {
      header: 1,
    });

    console.log("XLSX parse complete:", sheet);
    processXLSXData(sheet);
    document.getElementById("csvStatus").textContent = file.name;
  };
  reader.readAsArrayBuffer(file);
}

function processFeaturePoints(data) {
  featurePoints = data.reduce((acc, row) => {
    if (row.Symbol && row.Name) {
      const key = `${row.Symbol}-${row.Name}`;
      acc[key] = {
        Objectid: row.Objectid,
        height: row.Height,
        longitude: row.Longitude,
        latitude: row.Latitude,
        elevation: row.Elevation,
      };
    }
    return acc;
  }, {});
  console.log("Feature points:", featurePoints);
}

function processXLSXData(sheet) {
  sheet.forEach((row, index) => {
    if (index === 0) return;
    const [Objectid, Symbol, Name, Height, Longitude, Latitude, Elevation] =
      row;
    if (Symbol && Name) {
      const key = `${Symbol}-${Name}`;
      featurePoints[key] = {
        Objectid: Objectid,
        height: Height,
        longitude: Longitude,
        latitude: Latitude,
        elevation: Elevation,
      };
    }
  });
  console.log("Feature points:", featurePoints);
}

// 初始化
document.addEventListener("DOMContentLoaded", function () {
  setupEventListeners();
});
