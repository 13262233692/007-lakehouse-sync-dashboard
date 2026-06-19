<template>
  <div class="stat-card">
    <div class="stat-icon" :style="{ backgroundColor: bgColor }">
      <el-icon :size="24"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-content">
      <div class="stat-value">
        <span class="value-num">{{ displayValue }}</span>
        <span class="value-unit">{{ unit }}</span>
      </div>
      <div class="stat-label">{{ label }}</div>
      <div class="stat-delta" :class="deltaClass">
        <el-icon v-if="delta !== 0"><component :is="delta > 0 ? 'Top' : 'Bottom'" /></el-icon>
        <span>{{ Math.abs(delta) }}% 较昨日</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  unit: { type: String, default: '' },
  icon: { type: String, default: 'DataAnalysis' },
  color: { type: String, default: '#3b82f6' },
  delta: { type: Number, default: 0 }
})

const bgColor = computed(() => props.color + '20')

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const deltaClass = computed(() => {
  if (props.delta === 0) return 'neutral'
  return props.delta > 0 ? 'up' : 'down'
})
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background-color: #1a2332;
  border: 1px solid #2a3a52;
  border-radius: 8px;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    border-color: #3b82f6;
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e6edf3;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;

  .value-num {
    font-size: 28px;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1.2;
  }

  .value-unit {
    font-size: 14px;
    color: #8b98a9;
    font-weight: 500;
  }
}

.stat-label {
  font-size: 13px;
  color: #8b98a9;
  margin-bottom: 6px;
}

.stat-delta {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;

  &.up {
    color: #10b981;
  }

  &.down {
    color: #ef4444;
  }

  &.neutral {
    color: #8b98a9;
  }

  .el-icon {
    font-size: 12px;
  }
}
</style>
