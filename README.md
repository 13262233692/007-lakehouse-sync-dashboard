# Lakehouse Sync Dashboard

Lakehouse 数据湖同步任务监控与管理平台。提供多数据源（Hive、OSS、TableStore、MySQL 等）之间数据资产的可视化管理、存储容量监控、同步任务追踪。

## 项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Lakehouse Sync Dashboard                      │
├─────────────────────┬─────────────────────────────┬─────────────────┤
│     Frontend        │          Backend            │   Hive Metastore│
│   (Vue3 + Nginx)    │  (FastAPI + SQLite/aiosqlite)│                 │
│   Port: 8080        │        Port: 8000           │   Port: 9083    │
├─────────────────────┴─────────────────────────────┴─────────────────┤
│                        Docker Network                                │
└─────────────────────────────────────────────────────────────────────┘

请求流程:
  浏览器 → Nginx (8080)
           ├─ /              → 静态文件 (dist/)
           └─ /api/*         → FastAPI Backend (8000)
                                 ├─ 查询 SQLite 数据库
                                 │   ├─ data_assets (数据资产)
                                 │   ├─ asset_columns (字段定义)
                                 │   ├─ asset_partitions (分区信息)
                                 │   ├─ sync_tasks (同步任务)
                                 │   └─ storage_trends (存储趋势)
                                 └─ 连接 Hive Metastore (9083)
```

## 功能特性

- **总览大屏** — 总存储容量、数据表总数、文件总数、今日同步次数等核心指标
- **存储来源占比** — 饼图展示 Hive / TableStore / OSS 各存储层容量分布
- **容量趋势分析** — 最近 30 天存储容量、文件数、数据表数变化趋势
- **存储树状图** — 按存储层 → 数据库 → 数据表 → 分层次级浏览资产目录
- **数据字典检索** — 支持按表名、注释、字段名、字段注释关键字搜索
- **表详情面板** — 查看字段定义、分区列表、存储位置、格式等元数据
- **同步任务管理** — 全量/增量同步任务触发、历史记录查看、当前状态监控

## 本地开发环境搭建

### 1. 环境要求

| 工具 | 版本要求 |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 24+ |
| Docker Compose | 2.0+ |

### 2. 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 生成模拟数据（无真实环境时）
python sample_data.py

# 启动开发服务器 (http://localhost:8000)
python run.py
```

### 3. 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (http://localhost:5173)
npm run dev
```

前端开发服务器已配置 `/api` 代理到 `http://localhost:8000`。

### 4. 验证服务

后端 API 文档 (Swagger): http://localhost:8000/docs
后端 API 文档 (ReDoc): http://localhost:8000/redoc
前端页面: http://localhost:5173

## Docker Compose 启动

### 一键启动所有服务

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止所有服务
docker-compose down

# 停止并清除数据卷
docker-compose down -v
```

启动成功后访问：

| 服务 | 地址 |
|------|------|
| 前端 Dashboard | http://localhost:8080 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| Hive Metastore | thrift://localhost:9083 |

### Docker 容器说明

- **hive-metastore**: Apache Hive 4.0.0 Metastore 服务，端口 9083
- **backend**: Python FastAPI 应用 (入口 `app.main:app`)，端口 8000
- **frontend**: Nginx + Vue 3 构建产物 (多阶段构建)，端口 8080 → 80

## 配置说明

### 环境变量

后端服务支持以下环境变量（在 `docker-compose.yml` 或 `.env` 文件中配置）：

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `APP_NAME` | `Lakehouse Sync Dashboard` | 应用名称 |
| `API_V1_PREFIX` | `/api` | API 路由前缀 |
| `DEBUG` | `true` | 调试模式（开启 SQL 日志等） |
| `DATABASE_URL` | `sqlite+aiosqlite:///./lakehouse.db` | SQLite 异步数据库连接串 |
| `CORS_ORIGINS` | `http://localhost:3000,5173,127.0.0.1` | CORS 允许的来源列表 |
| `HIVE_METASTORE_HOST` | `localhost` | Hive Metastore 主机地址 |
| `HIVE_METASTORE_PORT` | `9083` | Hive Metastore 端口 |

### Nginx 配置

文件位置: `docker/nginx.conf`

- 静态文件服务: `/` → `/usr/share/nginx/html` (支持 SPA 前端路由)
- API 反向代理: `/api/*` → `http://backend:8000/api/*`
- GZIP 压缩: 已启用，压缩级别 6，最小 1KB

## API 接口列表

所有接口前缀: `/api`，统一响应格式:

```json
{ "code": 0, "message": "success", "data": {...} }
```

### 基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

### 数据资产接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/assets` | 分页获取资产列表，支持 `?source_type=hive&keyword=xxx` 筛选 |
| GET | `/assets/search` | 全文搜索（表名、FQN、注释、字段名、字段注释） |
| GET | `/assets/{id}` | 获取单个资产详情（含字段和分区） |
| GET | `/assets/{id}/columns` | 获取资产字段定义列表 |
| GET | `/assets/{id}/partitions` | 获取资产分区列表 |

### 统计接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/stats/overview` | 获取总览统计（总容量、表数、文件数、各存储层分布） |
| GET | `/stats/tree` | 获取资产树状结构（存储层→数据库→表→分区） |
| GET | `/stats/trend` | 获取最近 30 天存储趋势数据 |
| GET | `/stats/source-breakdown` | 按数据源类型统计容量分布 |

### 同步任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/sync/trigger` | 触发同步任务，`?task_type=full|incremental` |
| GET | `/sync/history` | 分页获取同步历史记录，支持 `?status=running` |
| GET | `/sync/status` | 获取当前同步状态（是否运行中、当前任务、上次完成任务） |

## 数据库模型

### DataAsset (数据资产)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | string | 表名 |
| fully_qualified_name | string | 完全限定名 (唯一) |
| source_type | string | 数据源类型: hive / oss / tablestore / mysql |
| storage_layer | string | 存储层: hive / oss / tablestore |
| database_name | string | 数据库名 |
| table_type | string | 表类型: MANAGED_TABLE / EXTERNAL_TABLE |
| location | string | 存储位置 URI |
| format | string | 文件格式: parquet / orc / json / avro |
| total_size_bytes | bigint | 总容量 (字节) |
| file_count | int | 文件数 |
| row_count | bigint | 行数 |
| partition_count | int | 分区数 |
| column_count | int | 字段数 |
| owner | string | 所有者 |
| tags | string | 标签 (逗号分隔) |

### SyncTask (同步任务)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| task_type | string | 任务类型: full / incremental |
| status | string | 状态: pending / running / completed / failed |
| started_at | datetime | 开始时间 |
| completed_at | datetime | 完成时间 |
| total_assets | int | 待同步资产总数 |
| processed_assets | int | 已处理资产数 |
| total_size_bytes | bigint | 已同步总容量 |
| error_message | string | 错误信息 |
| triggered_by | string | 触发者: manual / cron / system |

## 目录结构

```
007-lakehouse-sync-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py       # 路由聚合
│   │   │   ├── assets.py         # 数据资产接口
│   │   │   ├── deps.py           # 依赖注入 (DB session 等)
│   │   │   ├── stats.py          # 统计接口
│   │   │   └── sync.py           # 同步任务接口
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理 (Pydantic Settings)
│   │   ├── database.py           # SQLAlchemy 异步引擎
│   │   ├── main.py               # FastAPI 应用入口
│   │   ├── models.py             # ORM 数据模型
│   │   └── schemas.py            # Pydantic 响应 Schema
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py           # API 单元测试
│   ├── pyproject.toml            # Python 项目配置
│   ├── requirements.txt          # Python 依赖列表
│   ├── run.py                    # 本地开发启动脚本 (uvicorn --reload)
│   ├── sample_data.py            # 模拟数据生成脚本
│   └── lakehouse.db              # SQLite 数据库（运行时生成）
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── StatCard.vue      # 统计卡片
│   │   │   ├── PieChart.vue      # 饼图 (ECharts)
│   │   │   ├── TrendChart.vue    # 趋势折线图
│   │   │   ├── TreeChart.vue     # 树状结构图
│   │   │   ├── ColumnTable.vue   # 字段定义表格
│   │   │   └── PartitionTable.vue # 分区列表表格
│   │   ├── views/
│   │   │   ├── Dashboard.vue     # 总览大屏页
│   │   │   ├── DataDictionary.vue # 数据字典页
│   │   │   ├── StorageTree.vue   # 存储树页
│   │   │   └── TrendAnalysis.vue # 趋势分析页
│   │   ├── data/
│   │   │   └── mock.js           # 前端 Mock 数据
│   │   ├── router/
│   │   │   └── index.js          # Vue Router 配置
│   │   ├── styles/
│   │   │   └── dark-theme.scss   # 深色主题样式
│   │   ├── App.vue               # 根组件 (路由容器)
│   │   └── main.js               # Vue 应用入口
│   ├── index.html                # HTML 模板
│   ├── package.json              # 前端依赖配置
│   └── vite.config.js            # Vite 构建配置 (别名 + API 代理)
├── docker/
│   ├── Dockerfile.backend        # 后端镜像构建
│   ├── Dockerfile.frontend       # 前端镜像构建 (多阶段: node build → nginx)
│   └── nginx.conf                # Nginx 配置 (静态服务 + API 代理 + GZIP)
├── docker-compose.yml            # 服务编排配置
└── README.md                     # 项目说明文档
```

## 开发测试

### 使用模拟数据

没有真实 Hive / OSS / TableStore 环境时，可使用模拟数据快速启动开发：

```bash
cd backend
python sample_data.py
```

该脚本会创建 SQLite 数据库并填充：
- 6 个示例数据资产（用户行为日志、订单表、商品维度、用户画像、支付流水、原始点击流）
- 92 条字段定义
- 10 条分区信息
- 5 条同步任务（completed / running / failed）
- 90 条存储趋势记录（30 天 × 3 存储层）

### 运行后端测试

```bash
cd backend
pip install -e ".[test]"
pytest
```

## License

MIT
