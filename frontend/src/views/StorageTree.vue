<template>
  <div class="page-container">
    <el-page-header class="page-header" @back="$router.back()">
      <template #content>
        <div class="page-title">存储下钻分析</div>
      </template>
    </el-page-header>
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="tree-card">
          <template #header>存储目录</template>
          <el-tree
            :data="treeData"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="handleNodeClick"
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <el-icon v-if="data.type === 'folder'"><Folder /></el-icon>
                <el-icon v-else><Document /></el-icon>
                <span class="node-label">{{ node.label }}</span>
                <span class="node-size">{{ data.size }}</span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>
      <el-col :span="18">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-card shadow="hover" class="chart-card">
              <template #header>存储占比分析</template>
              <div ref="pieChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" class="chart-card">
              <template #header>层级存储分布</template>
              <div ref="barChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>
        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <span v-if="selectedNode">当前路径: {{ selectedNode.path }}</span>
            <span v-else>详细信息</span>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="名称">{{ selectedNode?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ selectedNode?.type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="大小">{{ selectedNode?.size || '-' }}</el-descriptions-item>
            <el-descriptions-item label="文件数">{{ selectedNode?.fileCount || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ selectedNode?.createdAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最后修改">{{ selectedNode?.updatedAt || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getTreeData } from '@/api/stats'

const treeData = ref([])
const selectedNode = ref(null)
const pieChartRef = ref(null)
const barChartRef = ref(null)
let pieChart = null
let barChart = null

const initPieChart = () => {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} GB ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      roseType: 'radius',
      itemStyle: { borderRadius: 8, borderColor: '#132342', borderWidth: 2 },
      label: { color: '#b8c5d1' },
      data: [
        { value: 420, name: 'ads' },
        { value: 310, name: 'dwd' },
        { value: 234, name: 'ods' },
        { value: 135, name: 'dim' },
        { value: 80, name: 'dws' }
      ],
      color: ['#00d4ff', '#00ff9d', '#ffb020', '#a855f7', '#f472b6']
    }]
  })
}

const initBarChart = () => {
  if (!barChartRef.value) return
  barChart = echarts.init(barChartRef.value)
  barChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
    },
    yAxis: {
      type: 'category',
      data: ['热数据', '温数据', '冷数据', '归档数据'],
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#b8c5d1' }
    },
    series: [{
      type: 'bar',
      barWidth: '50%',
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
          { offset: 1, color: '#00d4ff' }
        ])
      },
      data: [680, 430, 280, 120]
    }]
  })
}

const handleNodeClick = (data) => {
  selectedNode.value = data
}

const handleResize = () => {
  pieChart?.resize()
  barChart?.resize()
}

onMounted(async () => {
  try {
    const data = await getTreeData()
    treeData.value = data.tree || []
  } catch (e) {
    treeData.value = [
      {
        id: 1, name: 'lakehouse', type: 'folder', path: '/lakehouse', size: '1.5 TB',
        fileCount: 1250, createdAt: '2025-01-15', updatedAt: '2026-06-18',
        children: [
          { id: 2, name: 'ods', type: 'folder', path: '/lakehouse/ods', size: '520 GB', fileCount: 380, createdAt: '2025-01-15', updatedAt: '2026-06-18', children: [] },
          { id: 3, name: 'dwd', type: 'folder', path: '/lakehouse/dwd', size: '410 GB', fileCount: 320, createdAt: '2025-02-10', updatedAt: '2026-06-18', children: [] },
          { id: 4, name: 'ads', type: 'folder', path: '/lakehouse/ads', size: '350 GB', fileCount: 280, createdAt: '2025-03-05', updatedAt: '2026-06-18', children: [] },
          { id: 5, name: 'dim', type: 'folder', path: '/lakehouse/dim', size: '120 GB', fileCount: 150, createdAt: '2025-02-20', updatedAt: '2026-06-17', children: [] },
          { id: 6, name: 'dws', type: 'folder', path: '/lakehouse/dws', size: '100 GB', fileCount: 120, createdAt: '2025-04-01', updatedAt: '2026-06-16', children: [] }
        ]
      }
    ]
  }
  initPieChart()
  initBarChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  barChart?.dispose()
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

  .tree-card {
    .tree-node {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: $text-secondary;

      .node-label {
        flex: 1;
        color: $text-primary;
      }

      .node-size {
        color: $text-tertiary;
        font-size: 12px;
      }
    }

    :deep(.el-tree) {
      background: transparent;
      color: $text-primary;

      .el-tree-node__content {
        height: 36px;

        &:hover {
          background: rgba(0, 212, 255, 0.08);
        }
      }

      .is-current > .el-tree-node__content {
        background: rgba(0, 212, 255, 0.15);
        color: $color-primary;
      }
    }
  }

  .chart-card {
    .chart-container {
      height: 300px;
      width: 100%;
    }
  }

  :deep(.el-descriptions) {
    .el-descriptions__label {
      background: rgba(0, 212, 255, 0.05);
      color: $text-secondary;
      border-color: $border-color;
    }

    .el-descriptions__content {
      color: $text-primary;
      border-color: $border-color;
    }

    .el-descriptions__cell {
      border-color: $border-color;
    }
  }
}
</style>
