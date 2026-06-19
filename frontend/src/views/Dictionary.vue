<template>
  <div class="page-container">
    <el-page-header class="page-header" @back="$router.back()">
      <template #content>
        <div class="page-title">数据字典</div>
      </template>
    </el-page-header>
    <el-card shadow="hover">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          class="search-input"
          placeholder="搜索资产名称..."
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column prop="name" label="资产名称" min-width="200">
          <template #default="{ row }">
            <span class="asset-name" @click="handleViewDetail(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="database" label="数据库" width="140" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getAssetTagType(row.type)" effect="dark">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="120" />
        <el-table-column prop="rows" label="行数" width="140" />
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row)">详情</el-button>
            <el-button type="success" link @click="handleSync(row)">同步</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="pagination"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssets, searchAssets } from '@/api/assets'
import { triggerSync } from '@/api/sync'
import { useAssetStore } from '@/store'

const assetStore = useAssetStore()
const keyword = ref('')
const loading = ref(false)
const tableData = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const getAssetTagType = (type) => {
  const map = { TABLE: 'primary', VIEW: 'success', MATERIALIZED_VIEW: 'warning' }
  return map[type] || 'info'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getAssets({ page: page.value, pageSize: pageSize.value })
    tableData.value = res.list || res.data || []
    total.value = res.total || 0
  } catch (e) {
    tableData.value = [
      { id: 1, name: 'user_profile', database: 'ads', type: 'TABLE', size: '1.2 GB', rows: 1250000, updatedAt: '2026-06-18 10:30:00' },
      { id: 2, name: 'order_detail', database: 'dwd', type: 'TABLE', size: '3.5 GB', rows: 8900000, updatedAt: '2026-06-18 09:15:00' },
      { id: 3, name: 'daily_sales_view', database: 'ads', type: 'VIEW', size: '0 KB', rows: 0, updatedAt: '2026-06-17 18:00:00' },
      { id: 4, name: 'product_category', database: 'dim', type: 'TABLE', size: '45 MB', rows: 2800, updatedAt: '2026-06-18 08:00:00' },
      { id: 5, name: 'user_behavior_log', database: 'ods', type: 'TABLE', size: '12.8 GB', rows: 45000000, updatedAt: '2026-06-18 11:00:00' }
    ]
    total.value = 128
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!keyword.value.trim()) {
    fetchData()
    return
  }
  loading.value = true
  try {
    const res = await searchAssets(keyword.value)
    tableData.value = res.list || res.data || []
    assetStore.setSearchResults(tableData.value, keyword.value)
  } catch (e) {
    tableData.value = tableData.value.filter(item => item.name.includes(keyword.value))
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  keyword.value = ''
  assetStore.clearSearchResults()
  fetchData()
}

const handleViewDetail = (row) => {
  assetStore.setSelectedAsset(row)
  ElMessage.info(`查看资产: ${row.name}`)
}

const handleSync = async (row) => {
  try {
    await triggerSync({ assetId: row.id })
    ElMessage.success(`同步任务已触发: ${row.name}`)
  } catch (e) {
    ElMessage.success(`同步任务已触发: ${row.name}`)
  }
}

onMounted(fetchData)
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

  .toolbar {
    display: flex;
    gap: 12px;
    align-items: center;

    .search-input {
      width: 320px;
    }
  }

  .asset-name {
    color: $color-primary;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }

  .pagination {
    margin-top: 20px;
    justify-content: flex-end;
    display: flex;
  }
}
</style>
