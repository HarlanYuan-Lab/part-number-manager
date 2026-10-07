# Part Number Manager V2 — 客户端（集中数据库版）

V2.0 客户端：连接你 NAS / 服务器上的集中 **PostgreSQL**，所有工程与零件数据都存
服务器，客户端本地**不保存任何数据文件**（仅可选项：本地记住登录用的配置）。

> **开源说明**：本文中的服务器地址、端口、数据库名、账号、密码均为**示例占位符**
> （如 `YOUR_SERVER_IP`、`CHANGE_ME_DB_PASSWORD`）。请把它们改成你自己的实际值。

---

## 目录结构

```
client\
├─ main.py                     程序入口（tkinter 桌面客户端）
├─ _test_v2.py                 数据层回归验证脚本（连接真实服务器自测）
├─ _test_import.py             V1.0 ↔ V2.0 数据迁移验证脚本
└─ part_manager\               分层包
    ├─ config.py               常量 + 服务器默认连接参数（此处改服务器信息）
    ├─ db.py                   PostgreSQL 连接管理 + 幂等建表/迁移
    ├─ models.py               Project / Part 模型
    ├─ repositories.py         数据访问（工程、零件号单调递增、避重）
    ├─ services.py             业务规则校验（前缀、后缀位数、互不相同等）
    ├─ auth.py                 应用账号 / 角色登录（默认账号见文件内注释）
    ├─ exporter.py             导出 Excel
    ├─ local_transfer.py       V1.0 SQLite ↔ 服务器 双向迁移
    └─ ui\                     界面（主题/面板/对话框/主窗口）
```

---

## 环境要求

- Python 3.10+（开发环境 3.12）
- 依赖：`tkinter`（Python 自带）、`openpyxl`、`psycopg[binary]`
  ```bash
  pip install openpyxl "psycopg[binary]"
  ```

## 运行（开发）

先修改 `part_manager/config.py` 中的服务器连接参数（`YOUR_SERVER_IP`、端口、
数据库名、角色、密码），然后：

```bash
python main.py
```

> 首次连接会自动在服务器上建表（`projects`、`parts`、`users`）并完成旧数据迁移，
> 无需手工建表。

---

## 界面与使用

窗口顶部是自定义选项卡（选中会放大）。共 4 个选项卡，**连接服务器在最前**：

1. **Connect to Server**：填服务器地址 / 端口 / 数据库 / 用户 / 密码，点
   **Connect to Server** 建立连接；连接成功后进入 **Account Login**，填应用账号
   与密码登录。提供 **Disconnect**（断开连接）与 **Logout**（仅退出登录、保留连接）。
   - 连接后可 **Create Account…**（含图片验证码，任何人可用，初始权限为 user）；
   - **Manage Users…** 仅管理员可用（改角色、重置密码、删除用户）。
   - 未登录时不显示任何数据库信息；创建/修改/删除零件、导出 Excel 均需登录。
2. **Projects**：在服务器上创建 / 删除工程。每个工程可自定义：
   - **Suffix Digits**（后缀位数，1–15）；
   - 三类前缀（Assembly / Part / Standard，**任意字母数字、互不相同**）。
   选中工程作为当前工程后，才能创建零件号。
3. **Create Part Number**：输入零件名、材料、描述、类型，自动生成零件号：
   `<前缀><零填充递增序号>`，每类从 `<前缀>00…001` 起递增，删除的号不复用，
   修改时若撞库内同号会自动递增避开。创建结果不弹窗，4 个字段（零件号/名称/
   材料/描述）各自**点击即复制**。
4. **Manage Parts**：搜索、编辑（单条 / Shift 或 Ctrl 多选批量）、删除、导出 Excel。

---

## 数据模型（服务器数据库）

- `projects`：工程，含三类前缀与每类递增计数器（只增不减，删除号不复用）。
- `parts`：零件，`UNIQUE(project_id, part_number)` 由数据库约束保证工程内不重号。
- `users`：应用账号（含角色 admin / user）。
- 删除工程自动级联删除其所有零件。

---

## 打包为 exe / 安装包

在 `client` 目录执行：

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name PartNumberManagerV2 --icon build_assets\app.ico main.py
```

再使用 `installer/setup.iss` 用 Inno Setup（`ISCC.exe`）编译安装包：

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
```

---

## 测试

- `python _test_v2.py` — 数据层回归（连接真实服务器、自动清理）。
- `python _test_import.py` — 用一份 V1.0 数据库（`_test_import.py` 里的 `V1`
  变量指向它）验证 V1.0 → 服务器导入、服务器 → V1.0 导出。
