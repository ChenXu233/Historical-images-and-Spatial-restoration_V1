// Toast弹窗模块

// 显示toast消息
function showToast(message, type = "info") {
  // 移除已存在的toast
  const existingToast = document.getElementById("toast");
  if (existingToast) {
    existingToast.remove();
  }

  // 创建toast元素
  const toast = document.createElement("div");
  toast.id = "toast";
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  // 添加样式
  toast.style.position = "fixed";
  toast.style.top = "20px";
  toast.style.right = "20px";
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "4px";
  toast.style.color = "white";
  toast.style.fontSize = "14px";
  toast.style.zIndex = "10000";
  toast.style.opacity = "0";
  toast.style.transition = "opacity 0.3s ease-in-out";

  // 根据类型设置背景色
  switch (type) {
    case "success":
      toast.style.backgroundColor = "#4CAF50";
      break;
    case "error":
      toast.style.backgroundColor = "#F44336";
      break;
    case "warning":
      toast.style.backgroundColor = "#FF9800";
      break;
    default:
      toast.style.backgroundColor = "#2196F3";
  }

  // 添加到页面
  document.body.appendChild(toast);

  // 显示动画
  setTimeout(() => {
    toast.style.opacity = "1";
  }, 100);

  // 30秒后自动隐藏
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3000);
  }, 3000);
}

// 导出函数供其他模块使用
window.showToast = showToast;
