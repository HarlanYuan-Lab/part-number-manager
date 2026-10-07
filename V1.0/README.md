# Part Number Manager V1.0 — 本地单机版（SQLite）

V1.0 是**本地单机版**零件号管理器：每个数据库就是一个独立的 SQLite 文件，所有数据
保存在本地，无需联网、无需安装服务器。适合个人 / 小型团队在单一电脑上使用。

---

## 功能

- **零件号创建**：输入零件名，自动生成零件号。
  - 装配体 Assembly → 前缀 `8`，零件 Part → 前缀 `2`，标准件 Standard → 前缀 `9`
    （前缀可在创建数据库时修改）。
  - 零件号由 **前缀 + 6 位序号** 组成，每类从 `000001` 起递增。
- **多数据库**：可自由创建 / 命名多个数据库，每个数据库的零件号独立编号。
- **零件管理**：
  - 按零件号或零件名搜索；
  - 删除零件号（被删除的号**不会**复用）；
  - 修改零件信息；
  - 支持 **Shift / Ctrl 多选**批量编辑与删除；
  - 导出整库为 **Excel** 表格；
  - 整库导入 / 导出备份（导入后自动接续最后号码）。
- **界面**：全英文，现代蓝主题，自定义选项卡（选中放大）。

---

## 目录结构

```
V1.0\
├─ source\                    源码
│   ├─ main.py                程序入口
│   ├─ PartNumberManager.spec PyInstaller 打包配置
│   └─ part_manager\          分层包
│       ├─ config.py          常量 + 默认前缀
│       ├─ db.py / repositories.py   数据库（SQLite）访问
│       ├─ models.py / services.py   模型与业务规则
│       ├─ exporter.py        导出 Excel
│       └─ ui\                界面（主题/面板/对话框/主窗口）
├─ installer\setup.iss        Inno Setup 安装包脚本
└─ build_assets\app.ico       应用图标
```

---

## 环境要求

- Python 3.10+
- 依赖：`tkinter`（Python 自带）、`openpyxl`
  ```bash
  pip install openpyxl
  ```

## 运行（开发）

```bash
python main.py
```

## 使用流程

1. 打开软件，在 **Databases** 页点击 **New Database**，输入数据库名并选择三类前缀
   （默认 Assembly=8 / Part=2 / Standard=9），创建后数据库文件默认保存在
   `%APPDATA%\PartNumberManager\` 下（创建时可选择保存路径）。
2. 在 **Create Part Number** 页输入零件名、材料、描述，选择类型，点击创建，
   自动生成零件号并显示（可点击复制）。
3. 在 **Manage Parts** 页搜索、修改、删除、多选批量操作，或导出 Excel / 整库备份。
4. 通过 **Import / Export** 迁移数据库到其它电脑（导入后自动接续号码）。

---

## 打包为 exe / 安装包

在 `source` 目录执行：

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name PartNumberManager --icon build_assets\app.ico main.py
```

再用 Inno Setup 编译 `installer/setup.iss`（默认安装到 `D:\Program Files\PartNumber Manager`，
安装时可自定义路径）：

```bash
ISCC.exe installer\setup.iss
```

---

## 与 V2.0 的区别

| | V1.0 | V2.0 |
|---|---|---|
| 数据库 | 本地 SQLite 文件 | 服务器集中 PostgreSQL |
| 部署 | 无需服务器 | 需在 NAS/服务器部署 Docker |
| 多人协作 | 不支持（单机） | 支持账号 / 权限 / 多人 |
| 数据位置 | 客户端本机 | 服务器集中管理 |

> 想单机快速用 → 用 V1.0；想团队集中管理 → 用 V2.0。V2.0 可导入 V1.0 的数据库
> （见 `V2.0/client/_test_import.py` 说明）。
