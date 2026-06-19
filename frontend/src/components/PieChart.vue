<template>
  <div ref="chartRef" class="pie-chart"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  colors: { type: Array, default: () => ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'] }
})

const emit = defineEmits(['click'])

const chartRef = ref(null)
let chartInstance = null

const getOption = () => {
  return {
    backgroundColor: 'transparent',
    title: {
      text: props.title,
      left: 'center',
      top: 10,
      textStyle: {
        color: '#e6edf3',
        fontSize: 14,
        fontWeight: 500
      }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a2332',
      borderColor: '#2a3a52',
      textStyle: { color: '#e6edf3' },
      formatter: (params) => {
        return `<div>${params.name}</div><div>容量: <b>${params.value} TB</b> (${params.percent}%)</div>`
      }
    },
    legend: {
      bottom: 10,
      left: 'center',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: '#8b98a9', fontSize: 12 },
      itemGap: 16
    },
    color: props.colors,
    series: [
      {
        name: '存储来源',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#111827',
          borderWidth: 2
        },
        label: {
          show: true,
          color: '#e6edf3',
          fontSize: 12,
          formatter: '{b}\n{d}%'
        },
        labelLine: {
          length: 8,
          length2: 10,
          lineStyle: { color: '#2a3a52' }
        },
        emphasis: {
          scale: true,
          scaleSize: 8,
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 20,
            shadowColor: 'rgba(59, 130, 246, 0.4)'
          }
        },
        data: props.data
      }
    ]
  }
}

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, 'dark')
  chartInstance.setOption(getOption())
  chartInstance.on('click', (params) => {
    emit('click', params)
  })
}

const resizeChart = () => {
  chartInstance && chartInstance.resize()
}

watch(() => props.data, () => {
  if (chartInstance) {
    chartInstance.setOption(getOption())
  }
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance && chartInstance.dispose()
})

defineExpose({
  resize: resizeChart
})
</script>

<style lang="scss" scoped>
.pie-chart {
  width: 100%;
  height: 100%;
  min-height: 280px;
}
</style>
