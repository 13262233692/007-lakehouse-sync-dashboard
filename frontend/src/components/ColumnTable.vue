<template>
  <div class="column-table-wrapper">
    <div v-if="title" class="table-title">{{ title }}</div>
    <el-table
      :data="columns"
      border
      stripe
      size="small"
      style="width: 100%"
      :header-cell-style="{ backgroundColor: '#111827', color: '#8b98a9' }"
    >
      <el-table-column
        prop="name"
        label="字段名"
        min-width="160"
        :show-overflow-tooltip="true"
      >
        <template #default="{ row }">
          <span class="col-name" :class="{ 'col-nullable': row.nullable }">{{ row.name }}</span>
          <el-tag v-if="!row.nullable" type="danger" size="small" effect="dark" class="pk-tag">NOT NULL</el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="type"
        label="类型"
        min-width="140"
      >
        <template #default="{ row }">
          <span class="col-type">{{ row.type }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="nullable"
        label="可空"
        width="80"
        align="center"
      >
        <template #default="{ row }">
          <el-icon :color="row.nullable ? '#10b981' : '#ef4444'">
            <component :is="row.nullable ? 'CircleCheck' : 'CircleClose'" />
          </el-icon>
        </template>
      </el-table-column>
      <el-table-column
        prop="comment"
        label="注释"
        min-width="200"
        :show-overflow-tooltip="true"
      >
        <template #default="{ row }">
          <span class="col-comment">{{ row.comment || '-' }}</span>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="columns.length === 0" class="empty-tip">
      <el-empty description="暂无字段信息" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  columns: { type: Array, default: () => [] },
  title: { type: String, default: '' }
})
</script>

<style lang="scss" scoped>
.column-table-wrapper {
  .table-title {
    font-size: 14px;
    font-weight: 500;
    color: #e6edf3;
    margin-bottom: 12px;
    padding-left: 4px;
    border-left: 3px solid #3b82f6;
  }

  .col-name {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    color: #e6edf3;
    font-weight: 500;
  }

  .col-type {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    color: #06b6d4;
    background-color: rgba(6, 182, 212, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .col-comment {
    font-size: 12px;
    color: #8b98a9;
  }

  .pk-tag {
    margin-left: 8px;
    --el-tag-font-size: 10px;
    padding: 0 4px;
    height: 18px;
    line-height: 16px;
  }

  .empty-tip {
    padding: 30px 0;
  }
}
</style>
