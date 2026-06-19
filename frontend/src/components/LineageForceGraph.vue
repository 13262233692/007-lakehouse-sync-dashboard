<template>
  <div class="force-graph-container" ref="chartContainer">
    <div ref="chartRef" class="chart"></div>
    <div v-if="loading" class="loading-mask">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <span>加载血缘网络...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  graphData: {
    type: Object,
    default: () => ({ nodes: [], links: [], categories: [] })
  },
  loading: {
    type: Boolean,
    default: false
  },
  height: {
    type: String,
    default: '600px'
  }
})

const emit = defineEmits(['node-click', 'edge-click'])

const chartRef = ref(null)
const chartContainer = ref(null)
let chartInstance = null

const storageLayerColors = {
  oss: '#10b981',
  hive: '#f59e0b',
  starrocks: '#00d4ff',
  tablestore: '#8b5cf6',
  unknown: '#6b7280'
}

const getNodeColor = (node) => {
  return storageLayerColors[node.storage_layer] || storageLayerColors.unknown
}

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value, 'dark')

  const option = buildOption(props.graphData)
  chartInstance.setOption(option)

  chartInstance.on('click', (params) => {
    if (params.dataType === 'node') {
      emit('node-click', params.data)
    } else if (params.dataType === 'edge') {
      emit('edge-click', params.data)
    }
  })

  chartInstance.on('dblclick', () => {
    chartInstance.dispatchAction({
      type: 'restore'
    })
  })
}

const buildOption = (data) => {
  const { nodes = [], links = [], categories = [] } = data

  const formattedNodes = nodes.map((node) => {
    const isMV = node.type === 'materialized_view'
    const color = getNodeColor(node)
    return {
      ...node,
      id: node.id,
      name: node.name,
      category: node.category || 0,
      symbolSize: node.symbolSize || (isMV ? 80 : 50),
      itemStyle: {
        color: color,
        borderColor: isMV ? '#fff' : color,
        borderWidth: isMV ? 3 : 1,
        shadowBlur: 20,
        shadowColor: color
      },
      label: {
        show: true,
        position: 'bottom',
        formatter: node.label || node.name,
        fontSize: 12,
        color: '#e5e7eb',
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        padding: [4, 8],
        borderRadius: 4
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 30,
          shadowColor: color,
          borderWidth: 4
        },
        label: {
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        formatter: (params) => {
          const n = params.data
          const props = n.properties || {}
          let html = `<div style="font-size:14px;font-weight:bold;color:${color};margin-bottom:8px;">${n.name}</div>`
          html += `<div style="font-size:12px;color:#9ca3af;">FQN: ${n.id}</div>`
          html += `<div style="font-size:12px;color:#9ca3af;">类型: ${n.type}</div>`
          html += `<div style="font-size:12px;color:#9ca3af;">存储层: ${n.storage_layer}</div>`
          if (props.refresh_type) {
            html += `<div style="font-size:12px;color:#9ca3af;">刷新类型: ${props.refresh_type}</div>`
          }
          if (props.refresh_interval) {
            const mins = Math.floor(props.refresh_interval / 60)
            html += `<div style="font-size:12px;color:#9ca3af;">刷新间隔: ${mins}分钟</div>`
          }
          if (props.is_active !== undefined) {
            html += `<div style="font-size:12px;color:${props.is_active ? '#10b981' : '#ef4444'};">状态: ${props.is_active ? '激活' : '未激活'}</div>`
          }
          return html
        }
      }
    }
  })

  const formattedLinks = links.map((link) => {
    const style = link.lineStyle || {}
    return {
      ...link,
      source: link.source,
      target: link.target,
      lineStyle: {
        color: style.color || '#00d4ff',
        width: style.width || 2,
        curveness: style.curveness || 0.2,
        type: style.type || 'solid',
        opacity: 0.8
      },
      label: link.label || { show: false },
      emphasis: {
        lineStyle: {
          width: (style.width || 2) * 2,
          opacity: 1
        }
      },
      tooltip: {
        formatter: (params) => {
          const d = params.data
          const delay = d.refresh_delay_seconds || 0
          const status = d.label?.status || 'normal'
          const statusMap = { normal: '正常', warning: '警告', delayed: '延迟' }
          const statusColor = { normal: '#10b981', warning: '#f59e0b', delayed: '#ef4444' }
          const timeStr = formatDelay(delay)
          let html = `<div style="font-size:14px;font-weight:bold;margin-bottom:8px;">数据流转</div>`
          html += `<div style="font-size:12px;">源: ${d.source}</div>`
          html += `<div style="font-size:12px;">目标: ${d.target}</div>`
          html += `<div style="font-size:12px;margin-top:4px;">刷新延迟: <b style="color:${statusColor[status]}">${timeStr}</b></div>`
          html += `<div style="font-size:12px;">状态: <span style="color:${statusColor[status]}">${statusMap[status]}</span></div>`
          if (d.transformation) {
            html += `<div style="font-size:11px;color:#9ca3af;margin-top:4px;max-width:300px;">转换: ${d.transformation.substring(0, 100)}${d.transformation.length > 100 ? '...' : ''}</div>`
          }
          return html
        }
      }
    }
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      borderWidth: 1,
      padding: 12,
      textStyle: {
        color: '#e5e7eb'
      }
    },
    legend: [{
      data: categories.map(c => c.name),
      top: 10,
      right: 20,
      textStyle: { color: '#9ca3af', fontSize: 12 },
      itemWidth: 16,
      itemHeight: 16
    }],
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      data: formattedNodes,
      links: formattedLinks,
      categories: categories,
      force: {
        repulsion: 400,
        gravity: 0.1,
        edgeLength: [120, 200],
        friction: 0.6
      },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 10],
      zoom: 1,
      minZoom: 0.3,
      maxZoom: 3,
      animation: true,
      animationDuration: 1500,
      animationEasingUpdate: 'quinticInOut'
    }]
  }
}

const formatDelay = (seconds) => {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
  return `${Math.floor(seconds / 86400)}天${Math.floor((seconds % 86400) / 3600)}时`
}

const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch(() => props.graphData, (newData) => {
  if (chartInstance && newData) {
    chartInstance.setOption(buildOption(newData), true)
  }
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initChart()
    window.addEventListener('resize', resizeChart)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

defineExpose({
  refresh: resizeChart
})
</script>

<style lang="scss" scoped>
.force-graph-container {
  position: relative;
  width: 100%;
  background: linear-gradient(135deg, rgba(10, 22, 40, 0.6) 0%, rgba(20, 40, 70, 0.4) 100%);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;

  .chart {
    width: 100%;
    height: v-bind(height);
  }

  .loading-mask {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 22, 40, 0.8);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    color: #00d4ff;
    font-size: 14px;
    z-index: 10;
  }
}
</style>
