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

### 交付归档与复盘报告
- 对已完成/已验收项目进行统一归档管理
- 记录交付文件、交付版本、交付日期、客户确认情况、复盘类型与复盘结论
- 支持按客户、配音员、时间区间查询筛选
- **统计图表**：
  - 项目完成率（环形图）
  - 返稿轮次分布（柱状图）
  - 客户确认周期（横向柱状图，按客户分组）
  - 归档项目复盘摘要（按复盘类型分组统计）
- **汇总指标**：已归档项目数、归档完成率、客户已确认/未确认数、平均确认周期、平均返稿轮次
- 编辑归档时自动更新归档时间

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

### archives 表
归档管理表，记录已完成/已验收项目的交付信息与复盘结论。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_id | INTEGER | 关联项目ID（唯一） |
| delivery_file | TEXT | 交付文件名称 |
| delivery_version | TEXT | 交付版本号 |
| delivery_date | TEXT | 交付日期 |
| client_confirmed | INTEGER | 客户是否确认（0=未确认，1=已确认） |
| client_confirm_date | TEXT | 客户确认日期 |
| review_type | TEXT | 复盘类型（质量问题/客户需求变更/沟通问题/流程问题/表现优秀/其他） |
| review_conclusion | TEXT | 复盘结论详情 |
| archived_at | TEXT | 归档时间（编辑时自动更新） |

**复盘类型说明：**
- **质量问题**：发音、音质等录音质量导致返稿
- **客户需求变更**：客户方需求调整导致返工
- **沟通问题**：信息传递不畅导致返稿
- **流程问题**：内部流程或加急处理相关
- **表现优秀**：配音员表现优异，一次通过或客户高度认可
- **其他**：未归类的其他原因
