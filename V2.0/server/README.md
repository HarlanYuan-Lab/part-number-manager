# Part Number Manager V2.0 — 集中数据库服务器（NAS / Docker）

本目录是 V2.0 的**服务器端**。V2.0 客户端不再使用本地 SQLite 文件，而是连接一台
集中 **PostgreSQL** 服务器（例如部署在飞牛 / fnOS 等 NAS 上），所有工程与零件数据
统一在服务器上管理，客户端不保存任何数据文件。

> **开源说明**：本文件中的 IP、端口、数据库名、账号、密码均为**示例占位符**。
> 请在下发使用前把它们改成你自己的实际值（标记为 `CHANGE ME` / `YOUR_SERVER_IP` 等）。

---

## 目录结构

```
part-number-manager\
├─ V1.0\                      本地单机版（SQLite，多数据库）
│   └─ source\...
├─ V2.0\
│   ├─ server\                服务器端（Docker Compose + 文档）
│   │   ├─ docker-compose.yml    数据库容器编排
│   │   └─ README.md             本说明
│   └─ client\                V2.0 客户端（连接本服务器）
└─ README.md                  仓库总览
```

---

## 服务器架构

| 组件 | 说明 |
|------|------|
| **PostgreSQL 16** | 集中存储；每个"工程"内零件号由数据库 `UNIQUE(project_id, part_number)` 保证唯一 |
| **Adminer** | 轻量 Web 管理界面，可在浏览器直观查看/维护数据 |
| 数据持久化 | 数据库文件存放在 NAS 上的专用数据子目录 |
| 端口 | PostgreSQL 默认 `5432`，Adminer 默认 `8080`（均可改） |

---

## 如何创建容器（在 NAS 上）

1. **放置**：把 `docker-compose.yml` 放到一个与数据库数据**分开**的目录（例如
   `/path/to/PN Manager/`）。
2. **改参数**：在 `docker-compose.yml` 中把以下占位符改成你自己的值：
   - `POSTGRES_PASSWORD: CHANGE_ME_DB_PASSWORD` → 你的数据库密码
   - `/path/to/PN Manager Server/data` → 你的数据目录
   - 端口、`YOUR_SERVER_IP` 等按需修改。
3. **首次/修复后初始化**：
   - 确保数据子目录（如 `/path/to/PN Manager Server/data`）**不存在或为空**。
   - 如果之前失败运行已在数据目录生成 PG 初始化文件（`PG_VERSION`、`base/`、
     `global/`、`pg_wal/`、`pg_hba.conf` 等），请先 `docker compose down`
     （或 `docker rm -f pn-manager-db`），清空数据目录，再重新 `docker compose up -d`。
4. **启动**：
   ```bash
   docker compose up -d
   ```
   （也可以把本文件导入 NAS Docker 应用的 Compose 界面创建。）

> **为什么必须用 `data/` 子目录**：PostgreSQL 启动时若挂载目录**非空**会拒绝初始化
> （报 `directory "/var/lib/postgresql/data" exists but is not empty`）。把编排文件
> 与数据目录分开，就不会触发该错误。

---

## 连接参数（V2.0 客户端使用）

在客户端 `client/part_manager/config.py` 中填写与服务器一致的值：

| 项     | 示例值             | 说明                     |
|--------|--------------------|--------------------------|
| Host   | `YOUR_SERVER_IP`   | 你的服务器 / NAS IP      |
| 端口   | `5432`             | PostgreSQL 端口          |
| 数据库 | `pnmanager`        | 数据库名                 |
| 用户   | `pnmanager`        | 拥有该库的数据库角色     |
| 密码   | `CHANGE_ME_DB_PASSWORD` | 数据库角色密码     |

---

## 网页管理（Adminer）

浏览器打开：`http://YOUR_SERVER_IP:8080`
- 系统：PostgreSQL
- 服务器：`pn-manager-db`（容器名）
- 用户名 / 数据库 / 密码：与连接参数一致

---

## 访问安全提醒

- 服务仅应在**内网**使用；如需外网访问，请通过反向代理并启用 HTTPS。
- 首次启动后请立即修改默认密码。
- 不要把你的真实账号、密码、内网 IP 提交到公开仓库。

---

## 下一步（V2.0 客户端）

容器就绪后，V2.0 客户端将：
- 连接服务器并在其上创建/管理多个"工程"；
- 每个工程独立维护前缀与递增序号，零件号唯一性由数据库约束保证；
- 所有数据集中存放于服务器，客户端无本地数据文件。
