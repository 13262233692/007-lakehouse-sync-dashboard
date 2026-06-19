<template>
  <div class="acceleration-network">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">
          <el-icon><Connection /></el-icon>
          加速网络拓扑
        </h2>
        <p class="page-desc">实时监控从 OSS/Hive 原始数据层到 StarRocks 物化视图的数据血缘与刷新延迟</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleRefresh" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新血缘
        </el-button>
        <el-tag :type="topologyHealthType" effect="dark" size="large">
          拓扑状态: {{ topologyHealthText }}
        </el-tag>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(0, 212, 255, 0.15); color: #00d4ff;">
          <el-icon :size="24"><Share /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ graphData.stats?.total_nodes || 0 }}</div>
          <div class="stat-label">数据节点</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">
          <el-icon :size="24"><Aim /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ graphData.stats?.total_edges || 0 }}</div>
          <div class="stat-label">血缘连线</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">
          <el-icon :size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ graphData.stats?.normal_edges || 0 }}</div>
          <div class="stat-label">正常同步</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">
          <el-icon :size="24"><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ graphData.stats?.warning_edges || 0 }}</div>
          <div class="stat-label">接近延迟</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">
          <el-icon :size="24"><CircleClose /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ graphData.stats?.delayed_edges || 0 }}</div>
          <div class="stat-label">延迟链路</div>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="graph-section">
        <div class="section-header">
          <h3>
            <el-icon><DataLine /></el-icon>
            数据流转力导向图
          </h3>
          <div class="section-tips">
            <span class="tip"><i class="tip-dot" style="background:#00d4ff"></i>StarRocks 内部表 / MV</span>
            <span class="tip"><i class="tip-dot" style="background:#10b981"></i>OSS 对象存储</span>
            <span class="tip"><i class="tip-dot" style="background:#f59e0b"></i>Hive 数仓</span>
            <span class="tip-divider">|</span>
            <span class="tip">拖拽节点 | 滚轮缩放 | 双击还原</span>
          </div>
        </div>
        <LineageForceGraph
          :graph-data="graphData"
          :loading="loading"
          height="620px"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
        />
      </div>

      <div class="side-panel">
        <div class="delay-section">
          <div class="section-header">
            <h3>
              <el-icon><Timer /></el-icon>
              刷新延迟监控
            </h3>
          </div>
          <div class="delay-list">
            <div
              v-for="(delay, key) in delayList"
              :key="key"
              class="delay-item"
              :class="delay.status"
            >
              <div class="delay-header">
                <span class="delay-status">
                  <el-icon v-if="delay.status === 'normal'" color="#10b981"><CircleCheck /></el-icon>
                  <el-icon v-else-if="delay.status === 'warning'" color="#f59e0b"><Warning /></el-icon>
                  <el-icon v-else color="#ef4444"><CircleClose /></el-icon>
                  <span>{{ delay.target.split('.').pop() }}</span>
                </span>
                <span class="delay-time">{{ formatDelay(delay.refresh_delay_seconds) }}</span>
              </div>
              <div class="delay-path">
                <span class="path-source">{{ delay.source.split('.').pop() }}</span>
                <el-icon><Right /></el-icon>
                <span class="path-target">{{ delay.target.split('.').pop() }}</span>
              </div>
              <div v-if="delay.refresh_interval" class="delay-interval">
                预期间隔: {{ Math.floor(delay.refresh_interval / 60) }}分钟
              </div>
            </div>
            <div v-if="delayList.length === 0" class="empty-state">
              <el-empty description="暂无延迟数据" :image-size="60" />
            </div>
          </div>
        </div>

        <div v-if="selectedNode" class="node-detail">
          <div class="section-header">
            <h3>
              <el-icon><InfoFilled /></el-icon>
              节点详情
            </h3>
            <el-button text size="small" @click="selectedNode = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="名称">
              <span style="color:#00d4ff;font-weight:600;">{{ selectedNode.name }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="FQN">{{ selectedNode.id }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ formatNodeType(selectedNode.type) }}</el-descriptions-item>
            <el-descriptions-item label="存储层">{{ selectedNode.storage_layer }}</el-descriptions-item>
            <el-descriptions-item v-if="selectedNode.database_name" label="数据库">
              {{ selectedNode.database_name }}
            </el-descriptions-item>
            <template v-if="selectedNode.properties">
              <el-descriptions-item v-if="selectedNode.properties.refresh_type" label="刷新类型">
                <el-tag size="small" :type="selectedNode.properties.is_active ? 'success' : 'info'">
                  {{ selectedNode.properties.refresh_type }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-if="selectedNode.properties.refresh_interval" label="刷新间隔">
                {{ Math.floor(selectedNode.properties.refresh_interval / 60) }} 分钟
              </el-descriptions-item>
              <el-descriptions-item v-if="selectedNode.properties.last_refresh_time" label="上次刷新">
                {{ formatTime(selectedNode.properties.last_refresh_time) }}
              </el-descriptions-item>
            </template>
          </el-descriptions>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection, Refresh, Share, Aim, CircleCheck, Warning, CircleClose,
  DataLine, Timer, Right, InfoFilled, Close
} from '@element-plus/icons-vue'
import LineageForceGraph from '@/components/LineageForceGraph.vue'
import { getLineageForceGraph, getLineageDelays } from '@/api/lineage'

const loading = ref(false)
const graphData = ref({ nodes: [], links: [], categories: [], stats: {}, delays: {} })
const selectedNode = ref(null)

const delayList = computed(() => {
  const delays = graphData.value.delays || {}
  return Object.values(delays).sort((a, b) => b.refresh_delay_seconds - a.refresh_delay_seconds)
})

const topologyHealthType = computed(() => {
  const stats = graphData.value.stats || {}
  if (stats.delayed_edges > 0) return 'danger'
  if (stats.warning_edges > 0) return 'warning'
  return 'success'
})

const topologyHealthText = computed(() => {
  const stats = graphData.value.stats || {}
  if (stats.delayed_edges > 0) return `${stats.delayed_edges} 条链路延迟`
  if (stats.warning_edges > 0) return `${stats.warning_edges} 条链路接近延迟`
  return '全部正常'
})

const fetchData = async (force = false) => {
  loading.value = true
  try {
    const [graphRes, delayRes] = await Promise.all([
      getLineageForceGraph(force),
      getLineageDelays(force)
    ])
    if (graphRes.code === 0) {
      graphData.value = graphRes.data
    }
    if (delayRes.code === 0) {
      graphData.value.delays = delayRes.data
    }
  } catch (e) {
    ElMessage.error('获取血缘数据失败')
  } finally {
    loading.value = false
  }
}

const handleRefresh = () => {
  fetchData(true)
  ElMessage.success('血缘网络已刷新')
}

const handleNodeClick = (node) => {
  selectedNode.value = node
}

const handleEdgeClick = (edge) => {
  console.log('Edge clicked:', edge)
}

const formatDelay = (seconds) => {
  if (!seconds || seconds < 0) return '0秒'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
  return `${Math.floor(seconds / 86400)}天${Math.floor((seconds % 86400) / 3600)}时`
}

const formatNodeType = (type) => {
  const types = {
    'materialized_view': '物化视图 (MV)',
    'table': '内部表',
    'external_table': '外部表',
    'unknown': '未知'
  }
  return types[type] || type
}

const formatTime = (t) => {
  if (!t) return '-'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN')
  } catch {
    return t
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.acceleration-network {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    .header-left {
      .page-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 22px;
        font-weight: 600;
        color: #fff;
        margin: 0;

        .el-icon {
          color: #00d4ff;
        }
      }
      .page-desc {
        margin: 8px 0 0;
        color: #94a3b8;
        font-size: 13px;
      }
    }

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;

    .stat-card {
      background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6));
      border: 1px solid rgba(0, 212, 255, 0.15);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      gap: 16px;
      align-items: center;
      transition: all 0.3s ease;

      &:hover {
        border-color: rgba(0, 212, 255, 0.4);
        transform: translateY(-2px);
      }

      .stat-icon {
        width: 52px;
        height: 52px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .stat-content {
        .stat-value {
          font-size: 26px;
          font-weight: 700;
          color: #fff;
          line-height: 1.2;
        }
        .stat-label {
          font-size: 12px;
          color: #94a3b8;
          margin-top: 4px;
        }
      }
    }
  }

  .main-content {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 20px;
  }

  .graph-section, .delay-section, .node-detail {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6));
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 20px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      font-weight: 600;
      color: #e5e7eb;
      margin: 0;

      .el-icon {
        color: #00d4ff;
      }
    }

    .section-tips {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 11px;
      color: #64748b;

      .tip {
        display: flex;
        align-items: center;
        gap: 4px;

        .tip-dot {
          display: inline-block;
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }
      }

      .tip-divider {
        color: #334155;
      }
    }
  }

  .side-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .delay-section {
    .delay-list {
      max-height: 380px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;

      &::-webkit-scrollbar {
        width: 6px;
      }
      &::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.2);
        border-radius: 3px;
      }
    }

    .delay-item {
      background: rgba(0, 0, 0, 0.3);
      border-left: 3px solid #10b981;
      border-radius: 8px;
      padding: 12px;

      &.warning {
        border-left-color: #f59e0b;
      }
      &.delayed {
        border-left-color: #ef4444;
      }

      .delay-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .delay-status {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          font-weight: 600;
          color: #e5e7eb;
        }
        .delay-time {
          font-size: 14px;
          font-weight: 700;
          font-family: monospace;
        }
      }
      .delay-path {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 6px;
        font-size: 11px;
        color: #64748b;

        .path-target {
          color: #00d4ff;
        }

        .el-icon {
          font-size: 12px;
          color: #475569;
        }
      }
      .delay-interval {
        margin-top: 4px;
        font-size: 10px;
        color: #475569;
      }
    }
  }

  .node-detail {
    :deep(.el-descriptions__label) {
      width: 90px;
      background: rgba(0, 0, 0, 0.3) !important;
      color: #94a3b8 !important;
      font-weight: 500;
    }
    :deep(.el-descriptions__content) {
      background: rgba(0, 0, 0, 0.15) !important;
      color: #e5e7eb;
    }
    :deep(.el-descriptions__body .el-descriptions__table) {
      outline: none;
    }
  }

  .empty-state {
    padding: 20px 0;
  }
}
</style>
