<template>
  <div ref="chartRef" class="trend-chart"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  xData: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  yAxisName: { type: String, default: '容量' },
  unit: { type: String, default: 'TB' },
  colors: { type: Array, default: () => ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6'] }
})

const emit = defineEmits(['click'])

const chartRef = ref(null)
let chartInstance = null

const getOption = () => {
  return {
    backgroundColor: 'transparent',
    title: {
      text: props.title,
      left: 10,
      top: 10,
      textStyle: {
        color: '#e6edf3',
        fontSize: 14,
        fontWeight: 500
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a2332',
      borderColor: '#2a3a52',
      textStyle: { color: '#e6edf3' },
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#8b98a9' },
        lineStyle: { color: '#2a3a52' }
      }
    },
    legend: {
      top: 10,
      right: 20,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: '#8b98a9', fontSize: 12 },
      itemGap: 16
    },
    grid: {
      left: 50,
      right: 50,
      top: 50,
      bottom: 40,
      containLabel: true
    },
    color: props.colors,
    xAxis: {
      type: 'category',
      data: props.xData,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#2a3a52' } },
      axisLabel: { color: '#8b98a9', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: props.yAxisName + `(${props.unit})`,
      nameTextStyle: { color: '#8b98a9', fontSize: 11 },
      axisLine: { show: false },
      axisLabel: { color: '#8b98a9', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(42, 58, 82, 0.5)', type: 'dashed' } }
    },
    series: props.series.map((s, idx) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: false,
      lineStyle: {
        width: 2,
        color: props.colors[idx % props.colors.length]
      },
      itemStyle: {
        color: props.colors[idx % props.colors.length],
        borderWidth: 2,
        borderColor: '#111827'
      },
      areaStyle: s.areaStyle ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: props.colors[idx % props.colors.length] + '40' },
          { offset: 1, color: props.colors[idx % props.colors.length] + '05' }
        ])
      } : undefined,
      emphasis: {
        focus: 'series',
        scale: true,
        scaleSize: 6
      }
    }))
  }
}

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, 'dark')
  chartInstance.setOption(getOption())
  chartInstance.on('click', (params) => emit('click', params))
}

const resizeChart = () => {
  chartInstance && chartInstance.resize()
}

watch(() => [props.xData, props.series], () => {
  if (chartInstance) chartInstance.setOption(getOption())
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance && chartInstance.dispose()
})

defineExpose({ resize: resizeChart })
</script>

<style lang="scss" scoped>
.trend-chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
