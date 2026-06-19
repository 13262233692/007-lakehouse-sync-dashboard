<template>
  <div class="page-container">
    <el-page-header class="page-header" @back="$router.back()">
      <template #content>
        <div class="page-title">趋势分析</div>
      </template>
    </el-page-header>
    <el-card shadow="hover" style="margin-bottom: 16px">
      <div class="filter-bar">
        <span class="filter-label">时间范围:</span>
        <el-radio-group v-model="timeRange" size="default">
          <el-radio-button value="7d">近7天</el-radio-button>
          <el-radio-button value="30d">近30天</el-radio-button>
          <el-radio-button value="90d">近90天</el-radio-button>
        </el-radio-group>
        <el-divider direction="vertical" />
        <span class="filter-label">指标:</span>
        <el-select v-model="metric" placeholder="选择指标" style="width: 180px">
          <el-option label="存储容量" value="storage" />
          <el-option label="同步任务数" value="syncCount" />
          <el-option label="数据行数" value="rows" />
        </el-select>
        <el-button type="primary" style="margin-left: 16px" @click="refreshCharts">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </el-card>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="mini-stat">
            <div class="stat-label">总增长</div>
            <div class="stat-value positive">+{{ trendStats.totalGrowth }}</div>
            <div class="stat-desc">较上周期</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="mini-stat">
            <div class="stat-label">日均增速</div>
            <div class="stat-value">{{ trendStats.dailyGrowth }}/天</div>
            <div class="stat-desc">平均日增量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="mini-stat">
            <div class="stat-label">峰值</div>
            <div class="stat-value">{{ trendStats.peakValue }}</div>
            <div class="stat-desc">峰值出现在 {{ trendStats.peakDate }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16">
      <el-col :span="24" style="margin-bottom: 16px">
        <el-card shadow="hover" class="chart-card">
          <template #header>趋势走势</template>
          <div ref="lineChartRef" class="chart-container-large"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>周同比分析</template>
          <div ref="compareChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>增长分布热力图</template>
          <div ref="heatmapChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getTrendData } from '@/api/stats'

const timeRange = ref('7d')
const metric = ref('storage')
const trendStats = ref({
  totalGrowth: '256 GB',
  dailyGrowth: '36.5 GB',
  peakValue: '89 GB',
  peakDate: '2026-06-15'
})

const lineChartRef = ref(null)
const compareChartRef = ref(null)
const heatmapChartRef = ref(null)
let lineChart = null
let compareChart = null
let heatmapChart = null

const generateDates = (days) => {
  const dates = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(`${d.getMonth() + 1}-${d.getDate()}`)
  }
  return dates
}

const generateRandomData = (days, base, variance) => {
  return Array.from({ length: days }, () => Math.floor(base + Math.random() * variance))
}

const initLineChart = () => {
  if (!lineChartRef.value) return
  lineChart = echarts.init(lineChartRef.value)
  const days = parseInt(timeRange.value) || 7
  lineChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['当前周期', '上一周期'], textStyle: { color: '#b8c5d1' }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: generateDates(days),
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
    },
    series: [
      {
        name: '当前周期',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: generateRandomData(days, 60, 40),
        lineStyle: { width: 3, color: '#00d4ff' },
        itemStyle: { color: '#00d4ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
          ])
        }
      },
      {
        name: '上一周期',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: generateRandomData(days, 50, 35),
        lineStyle: { width: 2, color: '#a855f7', type: 'dashed' },
        itemStyle: { color: '#a855f7' }
      }
    ]
  })
}

const initCompareChart = () => {
  if (!compareChartRef.value) return
  compareChart = echarts.init(compareChartRef.value)
  compareChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['本周', '上周'], textStyle: { color: '#b8c5d1' }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
    },
    series: [
      {
        name: '本周',
        type: 'bar',
        barWidth: '35%',
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#00d4ff' },
        data: [65, 72, 58, 80, 74, 45, 38]
      },
      {
        name: '上周',
        type: 'bar',
        barWidth: '35%',
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#6b7c93' },
        data: [55, 60, 62, 70, 68, 40, 32]
      }
    ]
  })
}

const initHeatmapChart = () => {
  if (!heatmapChartRef.value) return
  heatmapChart = echarts.init(heatmapChartRef.value)
  const hours = ['00', '04', '08', '12', '16', '20']
  const days = ['周日', '周六', '周五', '周四', '周三', '周二', '周一']
  const data = []
  for (let i = 0; i < 7; i++) {
    for (let j = 0; j < 6; j++) {
      data.push([j, i, Math.floor(Math.random() * 100)])
    }
  }
  heatmapChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { position: 'top' },
    grid: { height: '55%', top: '10%' },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      textStyle: { color: '#b8c5d1' },
      inRange: {
        color: ['#0f1f38', '#00d4ff', '#00ff9d']
      }
    },
    series: [{
      name: '活跃度',
      type: 'heatmap',
      data: data,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 212, 255, 0.5)' }
      }
    }]
  })
}

const refreshCharts = async () => {
  try {
    await getTrendData({ range: timeRange.value, metric: metric.value })
  } catch (e) {}
  initLineChart()
}

const handleResize = () => {
  lineChart?.resize()
  compareChart?.resize()
  heatmapChart?.resize()
}

watch([timeRange, metric], () => {
  refreshCharts()
})

onMounted(() => {
  initLineChart()
  initCompareChart()
  initHeatmapChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  lineChart?.dispose()
  compareChart?.dispose()
  heatmapChart?.dispose()
})
</script>

<style lang="scss" scoped>
.page-container {
  .page-header {
    margin-bottom: 20px;

    :deep(.el-page-header__content) { color: $text-primary; }
    :deep(.el-page-header__left) { color: $text-secondary; }
  }

  .page-title {
    font-size: 18px;
    font-weight: 600;
  }

  .filter-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;

    .filter-label {
      color: $text-secondary;
      font-size: 14px;
      margin-right: 4px;
    }

    :deep(.el-radio-button__inner) {
      background: $bg-secondary;
      border-color: $border-color;
      color: $text-secondary;

      &:hover {
        color: $color-primary;
      }
    }

    :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
      background: $color-primary;
      border-color: $color-primary;
      color: #fff;
    }
  }

  .stat-card {
    .mini-stat {
      .stat-label {
        color: $text-secondary;
        font-size: 13px;
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 28px;
        font-weight: 700;
        color: $text-primary;
        margin-bottom: 4px;

        &.positive {
          color: $color-accent;
        }
      }

      .stat-desc {
        color: $text-tertiary;
        font-size: 12px;
      }
    }
  }

  .chart-card {
    .chart-container {
      height: 300px;
      width: 100%;
    }

    .chart-container-large {
      height: 360px;
      width: 100%;
    }
  }
}
</style>
