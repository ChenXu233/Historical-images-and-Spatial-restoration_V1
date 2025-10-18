<template>
  <div class="error-overlay" @click.self="handleClose">
    <div class="error-container" :class="`error-type-${type}`">
      <!-- 错误图标 -->
      <div class="error-icon">
        <svg
          v-if="type === 'error'"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path
            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
          />
        </svg>
        <svg
          v-else-if="type === 'warning'"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
        </svg>
        <svg
          v-else
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path
            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
          />
        </svg>
      </div>

      <!-- 错误标题 -->
      <h3 class="error-title">{{ title || "错误" }}</h3>

      <!-- 错误消息 -->
      <p class="error-message">{{ message }}</p>

      <!-- 操作按钮 -->
      <div class="error-actions">
        <button
          v-if="onRetry"
          class="error-button retry-button"
          @click="handleRetry"
        >
          重试
        </button>
        <button class="error-button close-button" @click="handleClose">
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
interface Props {
  message: string;
  title?: string;
  type?: "error" | "warning" | "info";
  onRetry?: () => void;
  onClose: () => void;
}
</script>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    message: string;
    title?: string;
    type?: "error" | "warning" | "info";
    onRetry?: () => void;
    onClose: () => void;
  }>(),
  {
    type: "error",
  }
);

const handleClose = () => {
  props.onClose();
};

const handleRetry = () => {
  if (props.onRetry) {
    props.onRetry();
  }
};
</script>

<style scoped>
.error-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.error-container {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  text-align: center;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.error-icon {
  margin-bottom: 16px;
}

.error-type-error .error-icon {
  color: #e74c3c;
}

.error-type-warning .error-icon {
  color: #f39c12;
}

.error-type-info .error-icon {
  color: #3498db;
}

.error-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #333;
}

.error-message {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.error-button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-button {
  background-color: #3498db;
  color: white;
}

.retry-button:hover {
  background-color: #2980b9;
}

.close-button {
  background-color: #ecf0f1;
  color: #333;
}

.close-button:hover {
  background-color: #bdc3c7;
}
</style>
