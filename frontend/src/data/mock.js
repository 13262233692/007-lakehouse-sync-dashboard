export const storageStats = {
  totalCapacity: 128.6,
  totalTables: 2847,
  totalFiles: 156892,
  todaySyncCount: 342
}

export const storageSourcePie = [
  { name: 'Hive', value: 68.5 },
  { name: 'TableStore', value: 35.2 },
  { name: 'OSS', value: 24.9 }
]

export const capacityTrend = () => {
  const data = []
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const base = 100 + (29 - i) * 0.8
    data.push({
      date: `${date.getMonth() + 1}/${date.getDate()}`,
      hive: +(base * 0.52 + Math.random() * 2).toFixed(1),
      tablestore: +(base * 0.28 + Math.random() * 1.5).toFixed(1),
      oss: +(base * 0.20 + Math.random() * 1).toFixed(1)
    })
  }
  return data
}

export const syncHistory = [
  { id: 1, tableName: 'dwd_order_detail', storageType: 'Hive', syncTime: '2026-06-19 14:32:18', status: 'success', rows: 128450 },
  { id: 2, tableName: 'dim_user_info', storageType: 'TableStore', syncTime: '2026-06-19 14:28:05', status: 'success', rows: 5620 },
  { id: 3, tableName: 'ods_log_raw', storageType: 'OSS', syncTime: '2026-06-19 14:15:42', status: 'success', rows: 892310 },
  { id: 4, tableName: 'dws_payment_day', storageType: 'Hive', syncTime: '2026-06-19 14:02:30', status: 'failed', rows: 0 },
  { id: 5, tableName: 'dim_product_sku', storageType: 'TableStore', syncTime: '2026-06-19 13:55:11', status: 'success', rows: 32840 },
  { id: 6, tableName: 'dwd_user_behavior', storageType: 'Hive', syncTime: '2026-06-19 13:40:22', status: 'success', rows: 456789 },
  { id: 7, tableName: 'ads_report_summary', storageType: 'OSS', syncTime: '2026-06-19 13:22:08', status: 'success', rows: 1280 },
  { id: 8, tableName: 'dim_region_info', storageType: 'TableStore', syncTime: '2026-06-19 13:10:45', status: 'success', rows: 420 }
]

export const dataDictionary = [
  {
    id: 1,
    tableName: 'dwd_order_detail',
    storageType: 'Hive',
    database: 'dwd',
    recordCount: 128450000,
    size: 15.6,
    comment: '订单明细表',
    createTime: '2025-12-01 10:00:00',
    updateTime: '2026-06-19 14:32:18',
    owner: 'data_team',
    columns: [
      { name: 'order_id', type: 'BIGINT', nullable: false, comment: '订单ID' },
      { name: 'user_id', type: 'BIGINT', nullable: false, comment: '用户ID' },
      { name: 'product_id', type: 'BIGINT', nullable: false, comment: '商品ID' },
      { name: 'sku_id', type: 'BIGINT', nullable: true, comment: 'SKU ID' },
      { name: 'quantity', type: 'INT', nullable: false, comment: '购买数量' },
      { name: 'unit_price', type: 'DECIMAL(10,2)', nullable: false, comment: '单价' },
      { name: 'total_amount', type: 'DECIMAL(12,2)', nullable: false, comment: '订单总金额' },
      { name: 'pay_amount', type: 'DECIMAL(12,2)', nullable: true, comment: '实付金额' },
      { name: 'order_status', type: 'TINYINT', nullable: false, comment: '订单状态' },
      { name: 'create_time', type: 'TIMESTAMP', nullable: false, comment: '创建时间' },
      { name: 'update_time', type: 'TIMESTAMP', nullable: true, comment: '更新时间' }
    ],
    partitions: [
      { name: 'dt', type: 'STRING', value: '2026-06-19', size: 2.1, fileCount: 128 },
      { name: 'dt', type: 'STRING', value: '2026-06-18', size: 2.3, fileCount: 135 },
      { name: 'dt', type: 'STRING', value: '2026-06-17', size: 2.0, fileCount: 120 },
      { name: 'dt', type: 'STRING', value: '2026-06-16', size: 1.9, fileCount: 115 },
      { name: 'dt', type: 'STRING', value: '2026-06-15', size: 2.2, fileCount: 130 }
    ]
  },
  {
    id: 2,
    tableName: 'dim_user_info',
    storageType: 'TableStore',
    database: 'dim',
    recordCount: 5620000,
    size: 3.2,
    comment: '用户维度表',
    createTime: '2025-11-15 09:30:00',
    updateTime: '2026-06-19 14:28:05',
    owner: 'user_team',
    columns: [
      { name: 'user_id', type: 'BIGINT', nullable: false, comment: '用户ID' },
      { name: 'user_name', type: 'VARCHAR(64)', nullable: false, comment: '用户名' },
      { name: 'nick_name', type: 'VARCHAR(128)', nullable: true, comment: '昵称' },
      { name: 'phone', type: 'VARCHAR(20)', nullable: true, comment: '手机号' },
      { name: 'email', type: 'VARCHAR(128)', nullable: true, comment: '邮箱' },
      { name: 'gender', type: 'TINYINT', nullable: true, comment: '性别' },
      { name: 'age', type: 'INT', nullable: true, comment: '年龄' },
      { name: 'city', type: 'VARCHAR(64)', nullable: true, comment: '城市' },
      { name: 'register_time', type: 'TIMESTAMP', nullable: false, comment: '注册时间' },
      { name: 'is_active', type: 'BOOLEAN', nullable: false, comment: '是否活跃' }
    ],
    partitions: []
  },
  {
    id: 3,
    tableName: 'ods_log_raw',
    storageType: 'OSS',
    database: 'ods',
    recordCount: 892310000,
    size: 125.8,
    comment: '原始日志表',
    createTime: '2025-10-01 00:00:00',
    updateTime: '2026-06-19 14:15:42',
    owner: 'log_team',
    columns: [
      { name: 'log_id', type: 'STRING', nullable: false, comment: '日志ID' },
      { name: 'user_id', type: 'BIGINT', nullable: true, comment: '用户ID' },
      { name: 'session_id', type: 'STRING', nullable: true, comment: '会话ID' },
      { name: 'event_type', type: 'STRING', nullable: false, comment: '事件类型' },
      { name: 'page_url', type: 'STRING', nullable: true, comment: '页面URL' },
      { name: 'refer_url', type: 'STRING', nullable: true, comment: '来源URL' },
      { name: 'ip', type: 'STRING', nullable: true, comment: 'IP地址' },
      { name: 'user_agent', type: 'STRING', nullable: true, comment: 'UA' },
      { name: 'device_type', type: 'STRING', nullable: true, comment: '设备类型' },
      { name: 'os_type', type: 'STRING', nullable: true, comment: '操作系统' },
      { name: 'browser_type', type: 'STRING', nullable: true, comment: '浏览器类型' },
      { name: 'event_time', type: 'TIMESTAMP', nullable: false, comment: '事件时间' },
      { name: 'ext_info', type: 'STRING', nullable: true, comment: '扩展信息(JSON)' }
    ],
    partitions: [
      { name: 'dt', type: 'STRING', value: '2026-06-19', size: 4.2, fileCount: 1024 },
      { name: 'dt', type: 'STRING', value: '2026-06-18', size: 4.5, fileCount: 1080 },
      { name: 'dt', type: 'STRING', value: '2026-06-17', size: 4.1, fileCount: 998 },
      { name: 'dt', type: 'STRING', value: '2026-06-16', size: 4.0, fileCount: 976 },
      { name: 'dt', type: 'STRING', value: '2026-06-15', size: 4.3, fileCount: 1045 }
    ]
  },
  {
    id: 4,
    tableName: 'dws_payment_day',
    storageType: 'Hive',
    database: 'dws',
    recordCount: 365000,
    size: 0.8,
    comment: '支付日汇总表',
    createTime: '2026-01-10 08:00:00',
    updateTime: '2026-06-19 14:02:30',
    owner: 'finance_team',
    columns: [
      { name: 'stat_date', type: 'STRING', nullable: false, comment: '统计日期' },
      { name: 'pay_channel', type: 'STRING', nullable: false, comment: '支付渠道' },
      { name: 'order_count', type: 'BIGINT', nullable: false, comment: '订单数' },
      { name: 'user_count', type: 'BIGINT', nullable: false, comment: '用户数' },
      { name: 'total_amount', type: 'DECIMAL(14,2)', nullable: false, comment: '总金额' },
      { name: 'avg_amount', type: 'DECIMAL(10,2)', nullable: false, comment: '平均金额' }
    ],
    partitions: [
      { name: 'dt', type: 'STRING', value: '2026-06-19', size: 0.02, fileCount: 4 },
      { name: 'dt', type: 'STRING', value: '2026-06-18', size: 0.02, fileCount: 4 },
      { name: 'dt', type: 'STRING', value: '2026-06-17', size: 0.02, fileCount: 4 }
    ]
  },
  {
    id: 5,
    tableName: 'dim_product_sku',
    storageType: 'TableStore',
    database: 'dim',
    recordCount: 328400,
    size: 0.5,
    comment: '商品SKU维度表',
    createTime: '2025-12-20 11:00:00',
    updateTime: '2026-06-19 13:55:11',
    owner: 'product_team',
    columns: [
      { name: 'sku_id', type: 'BIGINT', nullable: false, comment: 'SKU ID' },
      { name: 'product_id', type: 'BIGINT', nullable: false, comment: '商品ID' },
      { name: 'product_name', type: 'VARCHAR(256)', nullable: false, comment: '商品名称' },
      { name: 'category_id', type: 'BIGINT', nullable: false, comment: '类目ID' },
      { name: 'category_name', type: 'VARCHAR(128)', nullable: true, comment: '类目名称' },
      { name: 'brand_id', type: 'BIGINT', nullable: true, comment: '品牌ID' },
      { name: 'brand_name', type: 'VARCHAR(128)', nullable: true, comment: '品牌名称' },
      { name: 'price', type: 'DECIMAL(10,2)', nullable: false, comment: '价格' },
      { name: 'stock', type: 'INT', nullable: false, comment: '库存' },
      { name: 'status', type: 'TINYINT', nullable: false, comment: '状态' },
      { name: 'create_time', type: 'TIMESTAMP', nullable: false, comment: '创建时间' }
    ],
    partitions: []
  },
  {
    id: 6,
    tableName: 'dwd_user_behavior',
    storageType: 'Hive',
    database: 'dwd',
    recordCount: 456789000,
    size: 45.6,
    comment: '用户行为明细表',
    createTime: '2025-11-01 10:00:00',
    updateTime: '2026-06-19 13:40:22',
    owner: 'behavior_team',
    columns: [
      { name: 'behavior_id', type: 'BIGINT', nullable: false, comment: '行为ID' },
      { name: 'user_id', type: 'BIGINT', nullable: false, comment: '用户ID' },
      { name: 'product_id', type: 'BIGINT', nullable: true, comment: '商品ID' },
      { name: 'behavior_type', type: 'TINYINT', nullable: false, comment: '行为类型(1浏览2收藏3加购4购买)' },
      { name: 'duration', type: 'INT', nullable: true, comment: '停留时长(秒)' },
      { name: 'source_type', type: 'TINYINT', nullable: true, comment: '来源类型' },
      { name: 'behavior_time', type: 'TIMESTAMP', nullable: false, comment: '行为时间' }
    ],
    partitions: [
      { name: 'dt', type: 'STRING', value: '2026-06-19', size: 1.5, fileCount: 256 },
      { name: 'dt', type: 'STRING', value: '2026-06-18', size: 1.6, fileCount: 268 }
    ]
  }
]

export const storageTreeData = {
  name: '数据湖存储',
  capacity: 128.6,
  fileCount: 156892,
  children: [
    {
      name: 'Hive',
      type: 'hive',
      capacity: 68.5,
      fileCount: 85420,
      children: [
        {
          name: 'dwd',
          type: 'hive',
          capacity: 32.1,
          fileCount: 42180,
          children: [
            { name: 'dwd_order_detail', type: 'hive', capacity: 15.6, fileCount: 20480 },
            { name: 'dwd_user_behavior', type: 'hive', capacity: 16.5, fileCount: 21700 }
          ]
        },
        {
          name: 'dws',
          type: 'hive',
          capacity: 5.4,
          fileCount: 6820,
          children: [
            { name: 'dws_payment_day', type: 'hive', capacity: 0.8, fileCount: 820 },
            { name: 'dws_user_day', type: 'hive', capacity: 2.3, fileCount: 3000 },
            { name: 'dws_product_day', type: 'hive', capacity: 2.3, fileCount: 3000 }
          ]
        },
        {
          name: 'ads',
          type: 'hive',
          capacity: 2.0,
          fileCount: 3500,
          children: [
            { name: 'ads_report_summary', type: 'hive', capacity: 1.2, fileCount: 1800 },
            { name: 'ads_user_profile', type: 'hive', capacity: 0.8, fileCount: 1700 }
          ]
        },
        {
          name: 'tmp',
          type: 'hive',
          capacity: 29.0,
          fileCount: 32920,
          children: [
            { name: 'tmp_order_202606', type: 'hive', capacity: 15.0, fileCount: 16000 },
            { name: 'tmp_user_202606', type: 'hive', capacity: 14.0, fileCount: 16920 }
          ]
        }
      ]
    },
    {
      name: 'TableStore',
      type: 'tablestore',
      capacity: 35.2,
      fileCount: 42180,
      children: [
        {
          name: 'dim',
          type: 'tablestore',
          capacity: 18.2,
          fileCount: 21090,
          children: [
            { name: 'dim_user_info', type: 'tablestore', capacity: 3.2, fileCount: 5620 },
            { name: 'dim_product_sku', type: 'tablestore', capacity: 0.5, fileCount: 3284 },
            { name: 'dim_region_info', type: 'tablestore', capacity: 0.1, fileCount: 420 },
            { name: 'dim_category_tree', type: 'tablestore', capacity: 14.4, fileCount: 11766 }
          ]
        },
        {
          name: 'realtime',
          type: 'tablestore',
          capacity: 17.0,
          fileCount: 21090,
          children: [
            { name: 'rt_order_stream', type: 'tablestore', capacity: 8.5, fileCount: 10545 },
            { name: 'rt_user_stream', type: 'tablestore', capacity: 8.5, fileCount: 10545 }
          ]
        }
      ]
    },
    {
      name: 'OSS',
      type: 'oss',
      capacity: 24.9,
      fileCount: 29292,
      children: [
        {
          name: 'ods',
          type: 'oss',
          capacity: 23.5,
          fileCount: 28092,
          children: [
            { name: 'ods_log_raw', type: 'oss', capacity: 23.5, fileCount: 28092 }
          ]
        },
        {
          name: 'backup',
          type: 'oss',
          capacity: 1.4,
          fileCount: 1200,
          children: [
            { name: 'bak_202605', type: 'oss', capacity: 0.8, fileCount: 700 },
            { name: 'bak_202606', type: 'oss', capacity: 0.6, fileCount: 500 }
          ]
        }
      ]
    }
  ]
}

export const trendData = (days) => {
  const data = []
  const now = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const baseHive = 50 + (days - i) * 0.4
    const baseTs = 25 + (days - i) * 0.3
    const baseOss = 20 + (days - i) * 0.1
    data.push({
      date: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
      hiveCapacity: +(baseHive + Math.random() * 3).toFixed(1),
      hiveFiles: Math.floor(50000 + (days - i) * 800 + Math.random() * 2000),
      tsCapacity: +(baseTs + Math.random() * 2).toFixed(1),
      tsFiles: Math.floor(30000 + (days - i) * 500 + Math.random() * 1500),
      ossCapacity: +(baseOss + Math.random() * 1).toFixed(1),
      ossFiles: Math.floor(15000 + (days - i) * 200 + Math.random() * 800)
    })
  }
  return data
}
