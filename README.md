# 配音返稿追踪器

一个用于录音工作室的配音项目返稿追踪桌面应用，帮助团队记录配音项目的返稿次数、修改原因和最终交付情况，复盘返工成本。

## 技术栈

- Python 3.9+
- PySide6 (Qt for Python)
- PySide6-Fluent-Widgets (现代化UI组件库)
- SQLite (本地数据库)
- pandas (数据处理)
- matplotlib (图表可视化)

## 功能特性

### 项目管理
- 项目列表展示，支持多条件搜索筛选
- 新增、编辑、删除项目
- 项目字段：项目编号、项目名称、客户名称、配音员、初稿日期、预计交付日期、返稿状态、最终结果

### 返稿记录维护
- 每个项目可关联多条返稿记录
- 返稿记录字段：返稿日期、返稿原因、修改轮次、是否加急、处理说明
- 支持新增、编辑、删除返稿记录

### 统计分析
- 项目概览统计卡片（总项目数、返稿项目数、返稿率、总返稿次数、平均返稿轮次）
- 返稿原因分布饼图
- 项目状态分布柱状图
- 月度项目与返稿趋势图
- 配音员维度统计表

### 配音员维度
- 按配音员筛选查看项目
- 配音员个人统计数据
- 配音员项目列表

### 搜索筛选
- 关键字搜索（项目编号、名称、客户、配音员）
- 按返稿状态筛选
- 按配音员筛选

## 安装运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化测试数据（可选）

```bash
python init_test_data.py
```

### 3. 运行应用

```bash
python main.py
```

## 项目结构

```
cj88/
├── main.py                  # 主程序入口
├── main_window.py           # 主窗口和项目列表页
├── project_dialog.py        # 新增/编辑项目对话框
├── project_detail_dialog.py # 项目详情对话框（返稿记录列表）
├── revision_dialog.py       # 新增/编辑返稿记录对话框
├── stats_page.py            # 统计分析页面
├── voice_actor_page.py      # 配音员维度页面
├── database.py              # 数据库操作层
├── init_test_data.py        # 初始化测试数据脚本
├── requirements.txt         # 依赖列表
└── voice_tracker.db         # SQLite数据库文件（运行时生成）
```

## 数据库设计

### projects 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_no | TEXT | 项目编号（唯一） |
| project_name | TEXT | 项目名称 |
| client_name | TEXT | 客户名称 |
| voice_actor | TEXT | 配音员 |
| draft_date | TEXT | 初稿日期 |
| expected_delivery_date | TEXT | 预计交付日期 |
| revision_status | TEXT | 返稿状态 |
| final_result | TEXT | 最终结果 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### revisions 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 关联项目ID |
| revision_date | TEXT | 返稿日期 |
| reason | TEXT | 返稿原因 |
| round | INTEGER | 修改轮次 |
| is_urgent | INTEGER | 是否加急 |
| description | TEXT | 处理说明 |
| created_at | TEXT | 创建时间 |
