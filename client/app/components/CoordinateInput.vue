<template>
  <div class="input-group">
    <input
      type="text"
      v-model="pointName"
      placeholder="特征点名称"
      class="input-field"
    />
    <input
      type="text"
      v-model="longitude"
      placeholder="经度"
      class="input-field"
      :style="{
        backgroundColor: longitude ? '#ffe6e6' : '',
      }"
      @input="validateLongitude"
    />
    <input
      type="text"
      v-model="latitude"
      placeholder="纬度"
      class="input-field"
      :style="{
        backgroundColor: latitude ? '#ffe6e6' : '',
      }"
      @input="validateLatitude"
    />
    <div class="coordinate-hint">单位为度，小数部分为5位，如199.39048</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface Props {
  pointName: string;
  longitude: string;
  latitude: string;
}

interface Emits {
  (e: "update:pointName", value: string): void;
  (e: "update:longitude", value: string): void;
  (e: "update:latitude", value: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const pointName = computed({
  get: () => props.pointName,
  set: (value) => emit("update:pointName", value),
});

const longitude = computed({
  get: () => props.longitude,
  set: (value) => emit("update:longitude", value),
});

const latitude = computed({
  get: () => props.latitude,
  set: (value) => emit("update:latitude", value),
});

const validateLongitude = () => {
  // 验证逻辑已在模板中实现
};

const validateLatitude = () => {
  // 验证逻辑已在模板中实现
};
</script>

<style scoped>
.input-group {
  display: flex;
  flex-direction: column;
  gap: 10px; /* 统一输入框间距 */
}

.input-field {
  padding: 8px;
  width: calc(100% - 16px); /* 统一宽度 */
  border: 1px solid #ddd;
  border-radius: 4px;
  transition: border-color 0.3s;
}

.input-field:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.coordinate-hint {
  font-size: 12px;
  color: #666;
  margin-top: 3px;
}
</style>
