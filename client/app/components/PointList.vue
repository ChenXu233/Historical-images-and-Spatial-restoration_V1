<template>
  <div class="point-list">
    <div v-for="(point, index) in points" :key="index" class="point-item">
      <div>
        {{ point.name }} ({{ point.x }}, {{ point.y }})<br />
        <template v-if="point.longitude">
          经度: {{ point.longitude }}°
        </template>
        <template v-if="point.latitude"> 纬度: {{ point.latitude }}° </template>
      </div>
      <button @click="onRemovePoint(index)" class="remove-btn">删除</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Point } from "../utils/types";

interface Props {
  points: Point[];
}

interface Emits {
  (e: "removePoint", index: number): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const onRemovePoint = (index: number) => {
  emit("removePoint", index);
};
</script>

<style scoped>
.point-list {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #ddd;
  background: white;
  border-radius: 4px;
  padding: 5px;
}

.point-item {
  padding: 10px;
  margin: 5px 0;
  background: #f9f9f9;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remove-btn {
  margin-left: 10px;
  padding: 4px 8px;
  background-color: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.remove-btn:hover {
  background-color: #ff7875;
}
</style>
