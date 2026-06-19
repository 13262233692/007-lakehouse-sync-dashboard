<template>
  <div ref="chartRef" class="tree-chart"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  levelColors: {
    type: Object,
    default: () => ({
      hive: '#3b82f6',
      tablestore: '#06b6d4',
      oss: '#10b981'
    })
  }
})

const emit = defineEmits(['nodeClick', 'drillDown'])

const chartRef = ref(null)
let chartInstance = null

const processData = (node, level = 0) => {
  const color = node.type ? props.levelColors[node.type] || '#8b5cf6' : '#8b5cf6'
  const processed = {
    name: node.name,
    value: node.capacity || 0,
    fileCount: node.fileCount || 0,
    type: node.type || 'default',
    itemStyle: {
      color: color,
      borderColor: color,
      borderWidth: 2
    },
    label: {
      color: '#e6edf3',
      fontSize: level === 0 ? 16 : 13,
      fontWeight: level === 0 ? 700 : 500
    },
    lineStyle: {
      color: color + '80',
      width: 2
    }
  }
  if (node.children && node.children.length > 0) {
    processed.children = node.children.map(child => processData(child, level + 1))
  }
  return processed
}

const getOption = () => {
  const processedData = processData(props.data)
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a2332',
      borderColor: '#2a3a52',
      textStyle: { color: '#e6edf3' },
      formatter: (params) => {
        const d = params.data
        return `<div style="font-weight:600;margin-bottom:8px;font-size:14px;">${d.name}</div>
                <div>容量: <b>${d.value} TB</b></div>
                <div>文件数: <b>${(d.fileCount || 0).toLocaleString()}</b></div>
                <div style="color:#8b98a9;font-size:11px;margin-top:4px;">点击下钻</div>`
      }
    },
    series: [
      {
        type: 'tree',
        data: [processedData],
        top: '5%',
        left: '10%',
        bottom: '5%',
        right: '15%',
        layout: 'orthogonal',
        orient: 'LR',
        symbol: 'circle',
        symbolSize: 14,
        edgeShape: 'curve',
        edgeForkPosition: '63%',
        initialTreeDepth: 2,
        roam: true,
        expandAndCollapse: true,
        animationDuration: 550,
        animationDurationUpdate: 750,
        label: {
          position: 'left',
          verticalAlign: 'middle',
          align: 'right',
          backgroundColor: 'rgba(26, 35, 50, 0.9)',
          padding: [4, 8],
          borderRadius: 4,
          formatter: (params) => {
            const d = params.data
            return `{name|${d.name}}\n{info|${d.value}TB · ${(d.fileCount || 0).toLocaleString()}个}`
          },
          rich: {
            name: {
              color: '#e6edf3',
              fontSize: 13,
              fontWeight: 500,
              lineHeight: 18
            },
            info: {
              color: '#8b98a9',
              fontSize: 11,
              lineHeight: 16
            }
          }
        },
        leaves: {
          label: {
            position: 'right',
            align: 'left'
          }
        },
        emphasis: {
          focus: 'descendant',
          itemStyle: {
            shadowBlur: 16,
            shadowColor: 'rgba(59, 130, 246, 0.5)'
          },
          label: {
            fontWeight: 700
          }
        }
      }
    ]
  }
}

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, 'dark')
  chartInstance.setOption(getOption())
  chartInstance.on('click', (params) => {
    emit('nodeClick', params.data)
    emit('drillDown', params.data)
  })
}

const resizeChart = () => {
  chartInstance && chartInstance.resize()
}

watch(() => props.data, () => {
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
.tree-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}
</style>
