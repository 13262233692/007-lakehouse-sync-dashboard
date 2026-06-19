<template>
  <div class="page-container">
    <el-page-header class="page-header" @back="$router.back()">
      <template #content>
        <div class="page-title">总览大屏</div>
      </template>
    </el-page-header>
    <div class="dashboard-content">
      <el-row :gutter="16" class="stat-cards">
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <el-icon class="stat-icon icon-blue"><DataLine /></el-icon>
              <div class="stat-info">
                <div class="stat-value">{{ overview?.totalAssets || 0 }}</div>
                <div class="stat-label">资产总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <el-icon class="stat-icon icon-green"><Coin /></el-icon>
              <div class="stat-info">
                <div class="stat-value">{{ overview?.totalSize || '0 TB' }}</div>
                <div class="stat-label">存储总量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <el-icon class="stat-icon icon-orange"><Refresh /></el-icon>
              <div class="stat-info">
                <div class="stat-value">{{ overview?.syncToday || 0 }}</div>
                <div class="stat-label">今日同步</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-item">
              <el-icon class="stat-icon icon-purple"><Connection /></el-icon>
              <div class="stat-info">
                <div class="stat-value">{{ overview?.dataSources || 0 }}</div>
                <div class="stat-label">数据源</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16" class="charts-row">
        <el-col :span="12">
          <el-card class="chart-card" shadow="hover">
            <template #header>数据源分布</template>
            <div ref="sourceChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card" shadow="hover">
            <template #header>同步趋势</template>
            <div ref="trendChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getSourceBreakdown, getTrendData } from '@/api/stats'

const overview = ref(null)
const sourceChartRef = ref(null)
const trendChartRef = ref(null)
let sourceChart = null
let trendChart = null

const initSourceChart = (data) => {
  if (!sourceChartRef.value) return
  sourceChart = echarts.init(sourceChartRef.value)
  sourceChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: '#b8c5d1' }
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#132342', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold', color: '#e6f1ff' }
      },
      labelLine: { show: false },
      data: data || [
        { value: 35, name: 'MySQL' },
        { value: 25, name: 'PostgreSQL' },
        { value: 20, name: 'Hive' },
        { value: 15, name: 'S3' },
        { value: 5, name: '其他' }
      ],
      color: ['#00d4ff', '#00ff9d', '#ffb020', '#ff4757', '#a855f7']
    }]
  })
}

const initTrendChart = (data) => {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data?.dates || ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      data: data?.values || [120, 132, 101, 134, 90, 230, 210],
      lineStyle: { width: 3, color: '#00d4ff' },
      itemStyle: { color: '#00d4ff', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
        ])
      }
    }]
  })
}

const handleResize = () => {
  sourceChart?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  try {
    overview.value = await getOverview()
  } catch (e) {
    overview.value = { totalAssets: 128, totalSize: '2.4 TB', syncToday: 56, dataSources: 8 }
  }
  try {
    const sourceData = await getSourceBreakdown()
    initSourceChart(sourceData)
  } catch (e) {
    initSourceChart(null)
  }
  try {
    const trendData = await getTrendData()
    initTrendChart(trendData)
  } catch (e) {
    initTrendChart(null)
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  sourceChart?.dispose()
  trendChart?.dispose()
})
</script>

<style lang="scss" scoped>
.page-container {
  .page-header {
    margin-bottom: 20px;

    :deep(.el-page-header__content) {
      color: $text-primary;
    }

    :deep(.el-page-header__left) {
      color: $text-secondary;
    }
  }

  .page-title {
    font-size: 18px;
    font-weight: 600;
  }

  .dashboard-content {
    .stat-cards {
      margin-bottom: 16px;

      .stat-card {
        border-radius: 8px;

        .stat-item {
          display: flex;
          align-items: center;
          gap: 16px;

          .stat-icon {
            font-size: 36px;

            &.icon-blue { color: $color-primary; }
            &.icon-green { color: $color-accent; }
            &.icon-orange { color: $color-warning; }
            &.icon-purple { color: #a855f7; }
          }

          .stat-info {
            .stat-value {
              font-size: 28px;
              font-weight: 700;
              color: $text-primary;
              line-height: 1.2;
            }

            .stat-label {
              font-size: 13px;
              color: $text-secondary;
              margin-top: 4px;
            }
          }
        }
      }
    }

    .charts-row {
      .chart-card {
        border-radius: 8px;

        .chart-container {
          height: 320px;
          width: 100%;
        }
      }
    }
  }
}
</style>
