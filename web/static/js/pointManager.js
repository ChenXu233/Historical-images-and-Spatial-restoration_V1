// 点标注管理模块

// 全局变量
let points = [];
let annotations = {}; // 存储所有图片的标注信息
let currentImageName = ""; // 当前图片名称
let currentImageId = ""; // 当前图片ID
let featurePoints = {}; // 存储上传的坐标数据

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

// 导出函数和变量供其他模块使用
window.points = points;
window.annotations = annotations;
window.currentImageName = currentImageName;
window.currentImageId = currentImageId;
window.featurePoints = featurePoints;
window.updatePointList = updatePointList;
window.removePoint = removePoint;
window.saveAnnotations = saveAnnotations;
window.deleteAnnotations = deleteAnnotations;
