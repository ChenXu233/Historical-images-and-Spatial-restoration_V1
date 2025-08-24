// 图像处理和画布操作模块

// 全局变量
const canvas = document.getElementById("imageCanvas");
const ctx = canvas.getContext("2d");
const coordsDisplay = document.getElementById("coordinates");
let image = null;
let scale = 1;
let offsetX = 0;
let offsetY = 0;
let isDragging = false;
let lastX = 0;
let lastY = 0;

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
      // 转换点坐标以适应当前画布变换
      const displayX = point.x * scale + offsetX;
      const displayY = point.y * scale + offsetY;

      ctx.beginPath();
      ctx.arc(displayX, displayY, 3, 0, 2 * Math.PI);
      ctx.fillStyle = "red";
      ctx.fill();

      ctx.font = "12px Arial";
      ctx.fillStyle = "yellow";
      ctx.fillText(point.symbol, displayX + 5, displayY + 5);
    });

    ctx.restore();
  }
}

// 鼠标事件处理函数
function handleMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  // 调整坐标计算方式，考虑画布的缩放和偏移
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
      showToast("请先选择或输入特征点信息", "warning");
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
  // 调整坐标显示方式，使其与点标注位置一致
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
  // 修正鼠标位置计算，相对于画布
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const wheel = e.deltaY < 0 ? 1 : -1;
  const zoom = Math.exp(wheel * zoomIntensity);

  // 修正缩放中心点计算
  const newScale = scale * zoom;
  // 限制缩放范围
  const clampedScale = Math.max(0.1, Math.min(newScale, 3));

  // 计算缩放比例变化
  const scaleRatio = clampedScale / scale;

  // 更新偏移量以保持缩放中心点不变
  offsetX = mouseX - scaleRatio * (mouseX - offsetX);
  offsetY = mouseY - scaleRatio * (mouseY - offsetY);

  // 更新缩放比例
  scale = clampedScale;

  // 更新UI
  const zoomPercent = Math.round(scale * 100);
  document.getElementById("zoom").value = zoomPercent;
  document.getElementById("zoomValue").value = zoomPercent;

  redraw();
}

// 导出函数和变量供其他模块使用
window.canvas = canvas;
window.ctx = ctx;
window.coordsDisplay = coordsDisplay;
window.image = image;
window.scale = scale;
window.offsetX = offsetX;
window.offsetY = offsetY;
window.isDragging = isDragging;
window.lastX = lastX;
window.lastY = lastY;
window.fitImageToCanvas = fitImageToCanvas;
window.redraw = redraw;
window.handleMouseDown = handleMouseDown;
window.handleMouseMove = handleMouseMove;
window.handleMouseUp = handleMouseUp;
window.handleWheel = handleWheel;
