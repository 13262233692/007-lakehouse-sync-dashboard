import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random
import os

DB_PATH = Path(__file__).parent / "lakehouse_sync.db"

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS data_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        fully_qualified_name VARCHAR(512) NOT NULL UNIQUE,
        source_type VARCHAR(64) NOT NULL,
        storage_layer VARCHAR(64) NOT NULL,
        database_name VARCHAR(255),
        schema_name VARCHAR(255),
        table_type VARCHAR(64),
        location VARCHAR(1024),
        format VARCHAR(32),
        description TEXT,
        total_size_bytes BIGINT NOT NULL DEFAULT 0,
        file_count INTEGER NOT NULL DEFAULT 0,
        row_count BIGINT,
        partition_count INTEGER NOT NULL DEFAULT 0,
        column_count INTEGER NOT NULL DEFAULT 0,
        owner VARCHAR(255),
        tags VARCHAR(1024),
        last_updated_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        name VARCHAR(255) NOT NULL,
        data_type VARCHAR(128) NOT NULL,
        comment TEXT,
        is_nullable INTEGER NOT NULL DEFAULT 1,
        is_partition INTEGER NOT NULL DEFAULT 0,
        ordinal_position INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (asset_id) REFERENCES data_assets(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_partitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        name VARCHAR(512) NOT NULL,
        value VARCHAR(512),
        size_bytes BIGINT NOT NULL DEFAULT 0,
        file_count INTEGER NOT NULL DEFAULT 0,
        row_count BIGINT,
        location VARCHAR(1024),
        created_at TIMESTAMP,
        last_modified_at TIMESTAMP,
        FOREIGN KEY (asset_id) REFERENCES data_assets(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type VARCHAR(64) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        total_assets INTEGER NOT NULL DEFAULT 0,
        processed_assets INTEGER NOT NULL DEFAULT 0,
        total_size_bytes BIGINT NOT NULL DEFAULT 0,
        error_message TEXT,
        triggered_by VARCHAR(255),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS storage_trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stat_date VARCHAR(10) NOT NULL,
        storage_layer VARCHAR(64) NOT NULL,
        total_size_bytes BIGINT NOT NULL DEFAULT 0,
        total_files INTEGER NOT NULL DEFAULT 0,
        total_tables INTEGER NOT NULL DEFAULT 0,
        recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(stat_date, storage_layer)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_data_assets_name ON data_assets(name)",
    "CREATE INDEX IF NOT EXISTS ix_data_assets_source_type ON data_assets(source_type)",
    "CREATE INDEX IF NOT EXISTS ix_data_assets_storage_layer ON data_assets(storage_layer)",
    "CREATE INDEX IF NOT EXISTS ix_assets_source_storage ON data_assets(source_type, storage_layer)",
    "CREATE INDEX IF NOT EXISTS ix_storage_trends_stat_date ON storage_trends(stat_date)",
    "CREATE INDEX IF NOT EXISTS ix_storage_trends_storage_layer ON storage_trends(storage_layer)",
]

SAMPLE_ASSETS = [
    {
        "name": "user_behavior_log",
        "fully_qualified_name": "hive.default.user_behavior_log",
        "source_type": "hive",
        "storage_layer": "hive",
        "database_name": "default",
        "schema_name": None,
        "table_type": "EXTERNAL_TABLE",
        "location": "oss://lakehouse/warehouse/default/user_behavior_log",
        "format": "parquet",
        "description": "用户行为日志表，记录APP用户的点击、浏览、购买等行为",
        "total_size_bytes": 53687091200,
        "file_count": 1280,
        "row_count": 52800000,
        "partition_count": 30,
        "column_count": 12,
        "owner": "data_team",
        "tags": "user,behavior,log",
        "columns": [
            ("user_id", "bigint", "用户ID", 0, 0, 1),
            ("event_type", "string", "事件类型", 0, 0, 2),
            ("page_id", "string", "页面ID", 1, 0, 3),
            ("item_id", "bigint", "商品ID", 1, 0, 4),
            ("timestamp", "bigint", "事件时间戳", 0, 0, 5),
            ("session_id", "string", "会话ID", 1, 0, 6),
            ("device_type", "string", "设备类型", 1, 0, 7),
            ("os", "string", "操作系统", 1, 0, 8),
            ("app_version", "string", "APP版本", 1, 0, 9),
            ("ip", "string", "IP地址", 1, 0, 10),
            ("region", "string", "地区", 1, 0, 11),
            ("dt", "string", "日期分区", 0, 1, 12),
        ],
        "partitions": [
            ("dt=2024-01-15", "2024-01-15", 1789569706, 43, 1760000),
            ("dt=2024-01-14", "2024-01-14", 1895825408, 45, 1860000),
            ("dt=2024-01-13", "2024-01-13", 1932735283, 46, 1900000),
        ],
    },
    {
        "name": "orders",
        "fully_qualified_name": "hive.dw.orders",
        "source_type": "tablestore",
        "storage_layer": "hive",
        "database_name": "dw",
        "schema_name": None,
        "table_type": "MANAGED_TABLE",
        "location": "oss://lakehouse/warehouse/dw/orders",
        "format": "orc",
        "description": "订单事实表，同步自生产TableStore",
        "total_size_bytes": 21474836480,
        "file_count": 320,
        "row_count": 12500000,
        "partition_count": 90,
        "column_count": 18,
        "owner": "order_team",
        "tags": "order,fact",
        "columns": [
            ("order_id", "string", "订单ID", 0, 0, 1),
            ("user_id", "bigint", "用户ID", 0, 0, 2),
            ("total_amount", "decimal(18,2)", "订单总金额", 0, 0, 3),
            ("discount_amount", "decimal(18,2)", "优惠金额", 1, 0, 4),
            ("pay_amount", "decimal(18,2)", "实付金额", 0, 0, 5),
            ("status", "int", "订单状态", 0, 0, 6),
            ("pay_method", "string", "支付方式", 1, 0, 7),
            ("shipping_address", "string", "收货地址", 1, 0, 8),
            ("contact_name", "string", "联系人", 1, 0, 9),
            ("contact_phone", "string", "联系电话", 1, 0, 10),
            ("remark", "string", "备注", 1, 0, 11),
            ("created_at", "timestamp", "创建时间", 0, 0, 12),
            ("paid_at", "timestamp", "支付时间", 1, 0, 13),
            ("shipped_at", "timestamp", "发货时间", 1, 0, 14),
            ("completed_at", "timestamp", "完成时间", 1, 0, 15),
            ("canceled_at", "timestamp", "取消时间", 1, 0, 16),
            ("cancel_reason", "string", "取消原因", 1, 0, 17),
            ("dt", "string", "日期分区", 0, 1, 18),
        ],
        "partitions": [
            ("dt=2024-01-15", "2024-01-15", 239232860, 4, 138000),
            ("dt=2024-01-14", "2024-01-14", 249828737, 4, 144000),
            ("dt=2024-01-13", "2024-01-13", 254803968, 4, 147000),
        ],
    },
    {
        "name": "dim_products",
        "fully_qualified_name": "hive.dw.dim_products",
        "source_type": "mysql",
        "storage_layer": "hive",
        "database_name": "dw",
        "schema_name": None,
        "table_type": "MANAGED_TABLE",
        "location": "oss://lakehouse/warehouse/dw/dim_products",
        "format": "parquet",
        "description": "商品维度表，同步自生产MySQL",
        "total_size_bytes": 536870912,
        "file_count": 8,
        "row_count": 85600,
        "partition_count": 1,
        "column_count": 15,
        "owner": "product_team",
        "tags": "product,dimension",
        "columns": [
            ("product_id", "bigint", "商品ID", 0, 0, 1),
            ("product_name", "string", "商品名称", 0, 0, 2),
            ("category_id", "bigint", "分类ID", 0, 0, 3),
            ("category_name", "string", "分类名称", 1, 0, 4),
            ("brand_id", "bigint", "品牌ID", 1, 0, 5),
            ("brand_name", "string", "品牌名称", 1, 0, 6),
            ("price", "decimal(18,2)", "售价", 0, 0, 7),
            ("cost_price", "decimal(18,2)", "成本价", 1, 0, 8),
            ("status", "int", "上架状态", 0, 0, 9),
            ("weight", "double", "重量(kg)", 1, 0, 10),
            ("length", "double", "长(cm)", 1, 0, 11),
            ("width", "double", "宽(cm)", 1, 0, 12),
            ("height", "double", "高(cm)", 1, 0, 13),
            ("description", "string", "商品描述", 1, 0, 14),
            ("created_at", "timestamp", "创建时间", 0, 0, 15),
        ],
        "partitions": [],
    },
    {
        "name": "user_profile",
        "fully_qualified_name": "tablestore.analytics.user_profile",
        "source_type": "hive",
        "storage_layer": "tablestore",
        "database_name": "analytics",
        "schema_name": None,
        "table_type": "EXTERNAL_TABLE",
        "location": "tablestore://analytics/user_profile",
        "format": None,
        "description": "用户画像表，包含用户标签、偏好等信息",
        "total_size_bytes": 10737418240,
        "file_count": 0,
        "row_count": 2300000,
        "partition_count": 0,
        "column_count": 25,
        "owner": "analytics_team",
        "tags": "user,profile,tag",
        "columns": [
            ("user_id", "bigint", "用户ID", 0, 0, 1),
            ("gender", "string", "性别", 1, 0, 2),
            ("age_group", "string", "年龄段", 1, 0, 3),
            ("city_level", "string", "城市等级", 1, 0, 4),
            ("consumption_level", "string", "消费等级", 1, 0, 5),
            ("member_level", "string", "会员等级", 1, 0, 6),
            ("last_active_days", "int", "最近活跃天数", 1, 0, 7),
            ("total_orders", "int", "历史订单数", 1, 0, 8),
            ("total_spent", "decimal(18,2)", "历史消费总额", 1, 0, 9),
            ("preferred_categories", "string", "偏好品类", 1, 0, 10),
            ("preferred_brands", "string", "偏好品牌", 1, 0, 11),
            ("risk_score", "double", "风险评分", 1, 0, 12),
            ("tags", "string", "用户标签", 1, 0, 13),
        ],
        "partitions": [],
    },
    {
        "name": "payment_flow",
        "fully_qualified_name": "hive.ods.payment_flow",
        "source_type": "oss",
        "storage_layer": "hive",
        "database_name": "ods",
        "schema_name": None,
        "table_type": "EXTERNAL_TABLE",
        "location": "oss://data-ingest/payment/",
        "format": "json",
        "description": "支付流水表，从OSS原始数据导入",
        "total_size_bytes": 8589934592,
        "file_count": 560,
        "row_count": 8900000,
        "partition_count": 60,
        "column_count": 14,
        "owner": "finance_team",
        "tags": "payment,finance",
        "columns": [
            ("payment_id", "string", "支付流水号", 0, 0, 1),
            ("order_id", "string", "订单号", 0, 0, 2),
            ("user_id", "bigint", "用户ID", 0, 0, 3),
            ("amount", "decimal(18,2)", "支付金额", 0, 0, 4),
            ("currency", "string", "币种", 0, 0, 5),
            ("channel", "string", "支付渠道", 0, 0, 6),
            ("status", "string", "支付状态", 0, 0, 7),
            ("transaction_id", "string", "第三方交易号", 1, 0, 8),
            ("refund_amount", "decimal(18,2)", "退款金额", 1, 0, 9),
            ("paid_at", "timestamp", "支付时间", 1, 0, 10),
            ("refunded_at", "timestamp", "退款时间", 1, 0, 11),
            ("fail_reason", "string", "失败原因", 1, 0, 12),
            ("client_ip", "string", "客户端IP", 1, 0, 13),
            ("dt", "string", "日期分区", 0, 1, 14),
        ],
        "partitions": [
            ("dt=2024-01-15", "2024-01-15", 143654912, 9, 148000),
            ("dt=2024-01-14", "2024-01-14", 150994944, 10, 156000),
        ],
    },
    {
        "name": "raw_click_stream",
        "fully_qualified_name": "oss.landing.raw_click_stream",
        "source_type": "oss",
        "storage_layer": "oss",
        "database_name": "landing",
        "schema_name": None,
        "table_type": "EXTERNAL_TABLE",
        "location": "oss://raw-data/click-stream/",
        "format": "avro",
        "description": "原始点击流数据，OSS Landing层",
        "total_size_bytes": 1099511627776,
        "file_count": 15680,
        "row_count": 1056000000,
        "partition_count": 180,
        "column_count": 8,
        "owner": "data_platform",
        "tags": "raw,clickstream",
        "columns": [
            ("ts", "bigint", "时间戳", 0, 0, 1),
            ("uid", "string", "用户唯一标识", 1, 0, 2),
            ("sid", "string", "会话ID", 1, 0, 3),
            ("url", "string", "页面URL", 0, 0, 4),
            ("ref", "string", "来源URL", 1, 0, 5),
            ("ua", "string", "用户代理", 1, 0, 6),
            ("ip", "string", "IP地址", 1, 0, 7),
            ("dt", "string", "日期分区", 0, 1, 8),
        ],
        "partitions": [
            ("dt=2024-01-15", "2024-01-15", 6442450944, 92, 6180000),
            ("dt=2024-01-14", "2024-01-14", 6335076762, 90, 6080000),
        ],
    },
]

SAMPLE_SYNC_TASKS = [
    {
        "task_type": "full",
        "status": "completed",
        "started_at": -120,
        "completed_at": -30,
        "total_assets": 5,
        "processed_assets": 5,
        "total_size_bytes": 32212254720,
        "error_message": None,
        "triggered_by": "system",
    },
    {
        "task_type": "incremental",
        "status": "running",
        "started_at": -15,
        "completed_at": None,
        "total_assets": 5,
        "processed_assets": 3,
        "total_size_bytes": 21474836480,
        "error_message": None,
        "triggered_by": "cron",
    },
    {
        "task_type": "incremental",
        "status": "completed",
        "started_at": -1440,
        "completed_at": -1410,
        "total_assets": 5,
        "processed_assets": 5,
        "total_size_bytes": 20401094656,
        "error_message": None,
        "triggered_by": "cron",
    },
    {
        "task_type": "incremental",
        "status": "failed",
        "started_at": -2880,
        "completed_at": -2860,
        "total_assets": 5,
        "processed_assets": 2,
        "total_size_bytes": 8589934592,
        "error_message": "连接超时: 无法连接到 TableStore 实例 analytics",
        "triggered_by": "cron",
    },
    {
        "task_type": "full",
        "status": "completed",
        "started_at": -10080,
        "completed_at": -9900,
        "total_assets": 5,
        "processed_assets": 5,
        "total_size_bytes": 34359738368,
        "error_message": None,
        "triggered_by": "manual",
    },
]


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table_sql in TABLES:
        cursor.execute(table_sql)
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")


def generate_sample_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM asset_partitions")
    cursor.execute("DELETE FROM asset_columns")
    cursor.execute("DELETE FROM sync_tasks")
    cursor.execute("DELETE FROM storage_trends")
    cursor.execute("DELETE FROM data_assets")

    now = datetime.now()

    total_cols = 0
    total_parts = 0

    for asset in SAMPLE_ASSETS:
        columns = asset["columns"]
        partitions = asset["partitions"]
        total_cols += len(columns)
        total_parts += len(partitions)
        last_updated = now - timedelta(days=random.randint(0, 3), hours=random.randint(0, 23))
        created_at = now - timedelta(days=random.randint(30, 180))

        cursor.execute(
            """
            INSERT INTO data_assets (
                name, fully_qualified_name, source_type, storage_layer,
                database_name, schema_name, table_type, location, format,
                description, total_size_bytes, file_count, row_count,
                partition_count, column_count, owner, tags,
                last_updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset["name"], asset["fully_qualified_name"], asset["source_type"],
                asset["storage_layer"], asset["database_name"], asset["schema_name"],
                asset["table_type"], asset["location"], asset["format"],
                asset["description"], asset["total_size_bytes"], asset["file_count"],
                asset["row_count"], asset["partition_count"], asset["column_count"],
                asset["owner"], asset["tags"],
                last_updated.isoformat(), created_at.isoformat(),
            ),
        )
        asset_id = cursor.lastrowid

        for col in columns:
            cursor.execute(
                """
                INSERT INTO asset_columns (
                    asset_id, name, data_type, comment,
                    is_nullable, is_partition, ordinal_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (asset_id, col[0], col[1], col[2], col[3], col[4], col[5]),
            )

        for part in partitions:
            part_created = now - timedelta(days=random.randint(1, 30))
            part_modified = part_created + timedelta(hours=random.randint(1, 5))
            cursor.execute(
                """
                INSERT INTO asset_partitions (
                    asset_id, name, value, size_bytes, file_count,
                    row_count, location, created_at, last_modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id, part[0], part[1], part[2], part[3], part[4],
                    f"{asset['location']}/{part[0]}",
                    part_created.isoformat(), part_modified.isoformat(),
                ),
            )

    for task in SAMPLE_SYNC_TASKS:
        started_at = now + timedelta(minutes=task["started_at"]) if task["started_at"] else None
        completed_at = now + timedelta(minutes=task["completed_at"]) if task["completed_at"] else None
        created_at = started_at or (now - timedelta(minutes=10))

        cursor.execute(
            """
            INSERT INTO sync_tasks (
                task_type, status, started_at, completed_at,
                total_assets, processed_assets, total_size_bytes,
                error_message, triggered_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["task_type"], task["status"],
                started_at.isoformat() if started_at else None,
                completed_at.isoformat() if completed_at else None,
                task["total_assets"], task["processed_assets"], task["total_size_bytes"],
                task["error_message"], task["triggered_by"],
                created_at.isoformat(),
            ),
        )

    storage_layers = ["hive", "tablestore", "oss"]
    for i in range(30):
        stat_date = (now - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        for layer in storage_layers:
            base_size = {
                "hive": 75000000000,
                "tablestore": 10000000000,
                "oss": 1000000000000,
            }[layer]
            growth_factor = 1.0 + (29 - i) * 0.005
            size = int(base_size / growth_factor)
            files = int(size / 50000000)
            tables = 5 if layer == "hive" else (1 if layer == "tablestore" else 1)

            cursor.execute(
                """
                INSERT OR REPLACE INTO storage_trends (
                    stat_date, storage_layer, total_size_bytes,
                    total_files, total_tables, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (stat_date, layer, size, files, tables, now.isoformat()),
            )

    conn.commit()
    conn.close()

    print("模拟数据生成完成:")
    print(f"  - 数据资产: {len(SAMPLE_ASSETS)} 条")
    print(f"  - 字段定义: {total_cols} 条")
    print(f"  - 分区信息: {total_parts} 条")
    print(f"  - 同步任务: {len(SAMPLE_SYNC_TASKS)} 条")
    print(f"  - 存储趋势: {30 * len(storage_layers)} 条")


def main():
    print("开始生成 Lakehouse Sync Dashboard 模拟数据...")
    init_database()
    generate_sample_data()
    print("完成！")


if __name__ == "__main__":
    main()
