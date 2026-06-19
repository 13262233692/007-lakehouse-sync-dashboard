# Lakehouse Sync Dashboard

Lakehouse 数据湖同步任务监控与管理平台。提供多数据源（Hive、OSS、TableStore、MySQL 等）之间数据同步任务的可视化监控、进度追踪和日志管理。

## 项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Lakehouse Sync Dashboard                      │
├─────────────────────┬─────────────────────────────┬─────────────────┤
│     Frontend        │          Backend            │   Hive Metastore│
│   (Vue3 + Nginx)    │     (FastAPI + SQLite)      │                 │
│   Port: 8080        │        Port: 8000           │   Port: 9083    │
├─────────────────────┴─────────────────────────────┴─────────────────┤
│                        Docker Network                                │
└─────────────────────────────────────────────────────────────────────┘

请求流程:
  浏览器 → Nginx (8080)
           ├─ /              → 静态文件 (dist/)
           └─ /api/*         → FastAPI Backend (8000)
                                 ├─ 查询 SQLite 数据库
                                 └─ 连接 Hive Metastore (9083)
```

## 功能特性

- **任务概览仪表盘** — 统计同步任务总数、运行中、已完成、失败、待执行数量及已同步总行数
- **同步任务管理** — 查看所有同步任务列表，支持按状态筛选
- **任务进度追踪** — 实时显示每个任务的同步进度百分比、已同步行数
- **任务状态监控** — pending / running / completed / failed 多状态管理
- **同步日志查看** — 每个任务的详细执行日志（INFO / WARN / ERROR / DEBUG）
- **多数据源支持** — Hive、OSS、TableStore、MySQL 等数据源配置管理
- **模拟数据生成** — 无真实环境时一键生成开发测试数据

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

# 生成模拟数据
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

后端 API 文档: http://localhost:8000/docs
前端页面: http://localhost:5173

## Docker Compose 启动

### 一键启动所有服务

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

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
- **backend**: Python FastAPI 应用，端口 8000
- **frontend**: Nginx + Vue 构建产物，端口 8080 → 80

## 配置说明

### 环境变量

后端服务支持以下环境变量（在 `docker-compose.yml` 中配置）：

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `HIVE_METASTORE_HOST` | `hive-metastore` | Hive Metastore 主机地址 |
| `HIVE_METASTORE_PORT` | `9083` | Hive Metastore 端口 |
| `DATABASE_URL` | `sqlite:///./lakehouse.db` | SQLite 数据库连接串 |

### Nginx 配置

文件位置: `docker/nginx.conf`

- 静态文件服务: `/` → `/usr/share/nginx/html`
- API 反向代理: `/api/*` → `http://backend:8000/*`
- GZIP 压缩: 已启用，压缩级别 6，最小 1KB

## API 接口列表

### 基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务状态检查 |
| GET | `/api/health` | 健康检查，返回当前时间 |

### 同步任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 获取任务列表，支持 `?status=running` 筛选 |
| GET | `/api/tasks/{task_id}` | 获取单个任务详情 |
| GET | `/api/tasks/{task_id}/logs` | 获取任务同步日志 |

### 数据源接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sources` | 获取所有数据源配置列表 |

### 统计接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取任务统计概览（总数、各状态数量、已同步行数） |

### 数据模型

**SyncTask (同步任务)**
- `id`: 任务 ID
- `task_name`: 任务名称
- `source_type`: 源类型 (hive / oss / tablestore / mysql)
- `source_path`: 源路径
- `target_type`: 目标类型
- `target_path`: 目标路径
- `status`: 状态 (pending / running / completed / failed)
- `progress`: 进度 (0-100)
- `total_rows`: 总行数
- `synced_rows`: 已同步行数
- `error_message`: 错误信息
- `created_at` / `updated_at` / `last_sync_at`: 时间戳

## 目录结构

```
007-lakehouse-sync-dashboard/
├── backend/
│   ├── main.py                 # FastAPI 应用入口及路由定义
│   ├── run.py                  # 本地开发启动脚本 (uvicorn --reload)
│   ├── sample_data.py          # 模拟数据生成脚本
│   ├── requirements.txt        # Python 依赖列表
│   └── lakehouse.db            # SQLite 数据库（运行时生成）
├── frontend/
│   ├── src/
│   │   ├── App.vue             # 主页面组件
│   │   └── main.js             # Vue 应用入口
│   ├── index.html              # HTML 模板
│   ├── package.json            # 前端依赖配置
│   └── vite.config.js          # Vite 构建配置
├── docker/
│   ├── Dockerfile.backend      # 后端镜像构建
│   ├── Dockerfile.frontend     # 前端镜像构建 (多阶段)
│   └── nginx.conf              # Nginx 配置
├── docker-compose.yml          # 服务编排配置
└── README.md                   # 项目说明文档
```

## 开发测试

### 使用模拟数据

没有真实 Hive / OSS / TableStore 环境时，可使用模拟数据快速启动开发：

```bash
cd backend
python sample_data.py
```

该脚本会创建 SQLite 数据库并填充：
- 4 个示例数据源
- 5 个不同状态的同步任务（completed / running / failed / pending）
- 每个任务若干条同步日志

## License

MIT
