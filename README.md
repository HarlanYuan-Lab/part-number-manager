# Part Number Manager

一个用于 **零件号（Part Number）自动生成与集中管理** 的 Windows 桌面工具（tkinter）。

包含两个版本，共用一套现代蓝主题界面：

- **V1.0**：本地单机版，数据存本地 SQLite 文件，开箱即用、无需服务器。
- **V2.0**：集中数据库版，数据存 NAS / 服务器上的 PostgreSQL，支持账号与权限、
  多人协作，可导入 V1.0 数据库。

---

## 核心功能（两版通用）

- **自动生成零件号**：输入零件名即自动编号。
  - 三种零件类型：装配体 Assembly、零件 Part、标准件 Standard。
  - 每类可配置独立前缀（任意字母数字、互不相同）与**后缀位数**（V2）。
  - 每类从 `<前缀>00…001` 起递增；被删除的号**不复用**；修改时若撞库内同号
    自动递增避开。
- **零件管理**：按零件号 / 零件名搜索，编辑、删除（支持 Shift / Ctrl 多选批量），
  导出 **Excel**。
- **界面**：全英文，现代蓝主题，自定义选项卡（选中放大），创建结果**不弹窗**、
  零件号 / 名称 / 材料 / 描述各字段**点击即复制**。

---

## 版本选择

| | V1.0 | V2.0 |
|---|---|---|
| 数据库 | 本地 SQLite 文件 | 服务器集中 PostgreSQL |
| 需要服务器 | 否 | 是（NAS / Docker） |
| 多人协作 | 不支持（单机） | 账号 / 角色权限、多人 |
| 账号登录 | 无 | 有（管理员 / 普通用户） |
| 数据安全 | 本机文件 | 服务器统一备份管理 |
| 适用 | 个人、单机 | 团队、集中管理 |

> **想单机快速用 → 用 V1.0；想团队集中管理 → 用 V2.0。**

---

## 快速开始

### V1.0（单机）

```bash
cd V1.0/source
pip install openpyxl
python main.py
```

详见 [`V1.0/README.md`](V1.0/README.md)。

### V2.0（集中服务器 + 客户端）

1. 在 NAS 上用 `V2.0/server/docker-compose.yml` 启动 PostgreSQL（详见
   [`V2.0/server/README.md`](V2.0/server/README.md)）。
2. 修改客户端 `V2.0/client/part_manager/config.py` 中的服务器连接参数。
3. 安装依赖并运行：

```bash
cd V2.0/client
pip install openpyxl "psycopg[binary]"
python main.py
```

详见 [`V2.0/client/README.md`](V2.0/client/README.md)。

---

## 目录结构

```
part-number-manager\
├─ V1.0\                   本地单机版（SQLite）
│   ├─ README.md
│   └─ source\             Python 源码
├─ V2.0\                   集中数据库版（PostgreSQL）
│   ├─ README.md
│   ├─ client\             tkinter 客户端（连接服务器）
│   └─ server\             服务器端 Docker Compose
└─ LICENSE                 MIT 许可证
```

---

## ⚠️ 安全提醒（重要）

本仓库中出现的 IP、端口、数据库名、账号、密码均为**示例占位符**
（如 `YOUR_SERVER_IP`、`CHANGE_ME_DB_PASSWORD`、`admin` / `user1` 等）。

- 部署前请务必把这些占位符改成**你自己的实际值**。
- **不要**把你真实的内网 IP、数据库账号、密码提交到公开仓库。
- 服务器端口仅应在内网使用；如需外网访问，请通过反向代理并启用 HTTPS。
- 首次启动后请立即修改默认密码。

---

## 许可证

[MIT](LICENSE)
