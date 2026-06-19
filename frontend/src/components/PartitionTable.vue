<template>
  <div class="partition-table-wrapper">
    <div v-if="title" class="table-title">{{ title }}</div>
    <el-table
      :data="partitions"
      border
      stripe
      size="small"
      style="width: 100%"
      :header-cell-style="{ backgroundColor: '#111827', color: '#8b98a9' }"
    >
      <el-table-column
        prop="name"
        label="分区键"
        width="100"
      >
        <template #default="{ row }">
          <span class="part-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="type"
        label="类型"
        width="100"
      >
        <template #default="{ row }">
          <span class="part-type">{{ row.type }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="value"
        label="分区值"
        min-width="140"
      >
        <template #default="{ row }">
          <el-tag type="primary" effect="dark" size="small" round>{{ row.value }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="size"
        label="大小(TB)"
        width="120"
        align="right"
      >
        <template #default="{ row }">
          <span class="part-size">{{ row.size?.toFixed(2) || '0.00' }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="fileCount"
        label="文件数"
        width="120"
        align="right"
      >
        <template #default="{ row }">
          <span class="part-files">{{ (row.fileCount || 0).toLocaleString() }}</span>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="partitions.length === 0" class="empty-tip">
      <el-empty description="该表无分区信息" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  partitions: { type: Array, default: () => [] },
  title: { type: String, default: '' }
})
</script>

<style lang="scss" scoped>
.partition-table-wrapper {
  .table-title {
    font-size: 14px;
    font-weight: 500;
    color: #e6edf3;
    margin-bottom: 12px;
    padding-left: 4px;
    border-left: 3px solid #f59e0b;
  }

  .part-name {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    color: #e6edf3;
    font-weight: 500;
  }

  .part-type {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    color: #06b6d4;
  }

  .part-size {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    color: #10b981;
    font-weight: 500;
  }

  .part-files {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    color: #8b98a9;
  }

  .empty-tip {
    padding: 30px 0;
  }
}
</style>
