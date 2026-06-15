from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QDialog, QFormLayout, QLineEdit, QComboBox,
                               QTextEdit, QDialogButtonBox, QMessageBox,
                               QFileDialog, QCheckBox, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QPixmap
from qfluentwidgets import (CardWidget, TableWidget, ComboBox,
                            SubtitleLabel, TitleLabel, DateEdit,
                            PrimaryPushButton, PushButton, InfoBar, InfoBarPosition,
                            TabWidget, CheckBox, LineEdit)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams

import pandas as pd
import database
import os
from datetime import datetime

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False


class TemplateDialog(QDialog):
    def __init__(self, parent=None, template_id=None):
        super().__init__(parent)
        self.template_id = template_id
        self.setWindowTitle("编辑模板" if template_id else "新增模板")
        self.setMinimumWidth(550)
        self.init_ui()
        if template_id:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("如：大客户A标准模板")
        form.addRow("模板名称*：", self.name_edit)

        self.client_combo = QComboBox()
        self.client_combo.setEditable(True)
        clients = database.get_all_clients()
        self.client_combo.addItem("通用（所有客户）")
        for c in clients:
            self.client_combo.addItem(c)
        form.addRow("适用客户：", self.client_combo)

        self.project_type_edit = LineEdit()
        self.project_type_edit.setPlaceholderText("如：广告配音、有声书、纪录片等（可选）")
        form.addRow("项目类型：", self.project_type_edit)

        self.file_rule_edit = LineEdit()
        self.file_rule_edit.setPlaceholderText("支持占位符：{项目编号} {项目名称} {客户名称} {日期}，如：{客户名称}_{项目编号}_final.wav")
        form.addRow("交付文件命名规则：", self.file_rule_edit)

        self.version_rule_edit = LineEdit()
        self.version_rule_edit.setPlaceholderText("如：v1.0、final")
        form.addRow("默认交付版本：", self.version_rule_edit)

        self.review_type_combo = QComboBox()
        self.review_type_combo.addItem("")
        self.review_type_combo.addItems(['质量问题', '客户需求变更', '沟通问题', '流程问题', '表现优秀', '其他'])
        form.addRow("默认复盘类型：", self.review_type_combo)

        self.conclusion_edit = QTextEdit()
        self.conclusion_edit.setMaximumHeight(80)
        self.conclusion_edit.setPlaceholderText("支持占位符：{项目编号} {项目名称} {客户名称}")
        form.addRow("常用复盘结论模板：", self.conclusion_edit)

        self.confirm_process_edit = QTextEdit()
        self.confirm_process_edit.setMaximumHeight(60)
        self.confirm_process_edit.setPlaceholderText("如：1.初审→2.客户试听→3.修改→4.终验，可选")
        form.addRow("确认流程说明：", self.confirm_process_edit)

        self.default_check = CheckBox("设为默认模板")
        form.addRow("", self.default_check)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def load_data(self):
        tpl = database.get_archive_template_by_id(self.template_id)
        if not tpl:
            return
        self.name_edit.setText(tpl['template_name'])
        client = tpl.get('client_name', '') or ''
        idx = self.client_combo.findText(client if client else "通用（所有客户）")
        if idx >= 0:
            self.client_combo.setCurrentIndex(idx)
        elif client:
            self.client_combo.setCurrentText(client)
        self.project_type_edit.setText(tpl.get('project_type', '') or '')
        self.file_rule_edit.setText(tpl.get('delivery_file_rule', '') or '')
        self.version_rule_edit.setText(tpl.get('delivery_version_rule', '') or '')
        rt = tpl.get('review_type', '') or ''
        idx_rt = self.review_type_combo.findText(rt)
        if idx_rt >= 0:
            self.review_type_combo.setCurrentIndex(idx_rt)
        self.conclusion_edit.setPlainText(tpl.get('review_conclusion_template', '') or '')
        self.confirm_process_edit.setPlainText(tpl.get('confirm_process', '') or '')
        self.default_check.setChecked(bool(tpl.get('is_default', 0)))

    def validate_and_accept(self):
        if not self.name_edit.text().strip():
            InfoBar.warning(title="提示", content="请输入模板名称",
                            orient=Qt.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP, duration=2000, parent=self)
            return
        self.accept()

    def get_data(self):
        client_text = self.client_combo.currentText().strip()
        if client_text == "通用（所有客户）":
            client_text = ''
        return {
            'template_name': self.name_edit.text().strip(),
            'client_name': client_text,
            'project_type': self.project_type_edit.text().strip(),
            'delivery_file_rule': self.file_rule_edit.text().strip(),
            'delivery_version_rule': self.version_rule_edit.text().strip(),
            'review_type': self.review_type_combo.currentText().strip(),
            'review_conclusion_template': self.conclusion_edit.toPlainText().strip(),
            'confirm_process': self.confirm_process_edit.toPlainText().strip(),
            'is_default': 1 if self.default_check.isChecked() else 0,
        }


class TemplateExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TemplateExportPage")
        self.setStyleSheet("""
            TemplateExportPage { background-color: white; }
            QLabel { color: #333; }
        """)
        self.init_ui()
        self.load_templates()
        self.load_export_filters()
        self.load_export_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = TitleLabel("归档模板与导出中心")
        layout.addWidget(title)

        self.tab_widget = TabWidget(self)
        self.tab_widget.addTab(self.create_template_tab(), "归档模板管理")
        self.tab_widget.addTab(self.create_export_tab(), "数据导出中心")
        layout.addWidget(self.tab_widget, 1)

    def create_template_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        tip_card = CardWidget()
        tip_layout = QHBoxLayout(tip_card)
        tip_layout.setContentsMargins(15, 12, 15, 12)
        tip_label = QLabel("💡 提示：模板支持占位符 {项目编号} {项目名称} {客户名称} {日期}，新增归档时选择模板可自动填充相关字段。")
        tip_label.setStyleSheet("color: #666; font-size: 13px;")
        tip_layout.addWidget(tip_label)
        layout.addWidget(tip_card)

        btn_card = CardWidget()
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        btn_layout.setSpacing(10)

        self.add_tpl_btn = PrimaryPushButton("新增模板")
        self.add_tpl_btn.clicked.connect(self.on_add_template)
        btn_layout.addWidget(self.add_tpl_btn)

        self.edit_tpl_btn = PushButton("编辑模板")
        self.edit_tpl_btn.clicked.connect(self.on_edit_template)
        btn_layout.addWidget(self.edit_tpl_btn)

        self.delete_tpl_btn = PushButton("删除模板")
        self.delete_tpl_btn.clicked.connect(self.on_delete_template)
        btn_layout.addWidget(self.delete_tpl_btn)

        btn_layout.addStretch()

        self.tpl_count_label = QLabel("共 0 个模板")
        self.tpl_count_label.setStyleSheet("color: #666; font-size: 13px;")
        btn_layout.addWidget(self.tpl_count_label)

        layout.addWidget(btn_card)

        self.tpl_table = TableWidget()
        self.tpl_table.setColumnCount(9)
        self.tpl_table.setHorizontalHeaderLabels([
            "ID", "模板名称", "适用客户", "项目类型",
            "文件命名规则", "默认版本", "默认复盘类型", "确认流程", "默认"
        ])
        self.tpl_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tpl_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tpl_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tpl_table.verticalHeader().setVisible(False)
        self.tpl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tpl_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tpl_table.setColumnHidden(0, True)
        self.tpl_table.doubleClicked.connect(lambda _: self.on_edit_template())
        self.tpl_table.setAlternatingRowColors(True)

        layout.addWidget(self.tpl_table, 1)
        return widget

    def create_export_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        filter_card = CardWidget()
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 12, 15, 12)
        filter_layout.setSpacing(12)

        filter_title = QLabel("筛选条件：")
        filter_title.setStyleSheet("font-weight: bold; background-color: transparent;")
        filter_layout.addWidget(filter_title)

        date_start_label = QLabel("开始日期：")
        date_start_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(date_start_label)

        self.export_date_start = DateEdit()
        self.export_date_start.setCalendarPopup(True)
        first_day = QDate(QDate.currentDate().year(), QDate.currentDate().month(), 1)
        self.export_date_start.setDate(first_day)
        self.export_date_start.dateChanged.connect(self.on_export_filter_changed)
        filter_layout.addWidget(self.export_date_start)

        date_end_label = QLabel("结束日期：")
        date_end_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(date_end_label)

        self.export_date_end = DateEdit()
        self.export_date_end.setCalendarPopup(True)
        self.export_date_end.setDate(QDate.currentDate())
        self.export_date_end.dateChanged.connect(self.on_export_filter_changed)
        filter_layout.addWidget(self.export_date_end)

        client_label = QLabel("客户：")
        client_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(client_label)

        self.export_client_combo = ComboBox()
        self.export_client_combo.setMinimumWidth(130)
        self.export_client_combo.currentIndexChanged.connect(self.on_export_filter_changed)
        filter_layout.addWidget(self.export_client_combo)

        actor_label = QLabel("配音员：")
        actor_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(actor_label)

        self.export_actor_combo = ComboBox()
        self.export_actor_combo.setMinimumWidth(130)
        self.export_actor_combo.currentIndexChanged.connect(self.on_export_filter_changed)
        filter_layout.addWidget(self.export_actor_combo)

        filter_layout.addStretch()
        layout.addWidget(filter_card)

        export_btn_card = CardWidget()
        export_btn_layout = QHBoxLayout(export_btn_card)
        export_btn_layout.setContentsMargins(15, 10, 15, 10)
        export_btn_layout.setSpacing(10)

        self.export_excel_btn = PrimaryPushButton("📊 导出 Excel 报表")
        self.export_excel_btn.clicked.connect(self.on_export_excel)
        export_btn_layout.addWidget(self.export_excel_btn)

        self.export_charts_btn = PushButton("🖼  导出统计图表")
        self.export_charts_btn.clicked.connect(self.on_export_charts)
        export_btn_layout.addWidget(self.export_charts_btn)

        self.export_all_btn = PushButton("📦 一键导出全部")
        self.export_all_btn.clicked.connect(self.on_export_all)
        export_btn_layout.addWidget(self.export_all_btn)

        export_btn_layout.addStretch()

        self.export_count_label = QLabel("当前筛选共 0 条归档记录")
        self.export_count_label.setStyleSheet("color: #666; font-size: 13px;")
        export_btn_layout.addWidget(self.export_count_label)

        layout.addWidget(export_btn_card)

        self.summary_export_card = self.create_summary_card()
        layout.addWidget(self.summary_export_card)

        charts_title = SubtitleLabel("📈 统计图表预览")
        layout.addWidget(charts_title)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(15)

        self.preview_completion_card, self.preview_completion_fig, self.preview_completion_canvas = self.create_preview_chart("归档完成率")
        chart_row.addWidget(self.preview_completion_card, 1)

        self.preview_round_card, self.preview_round_fig, self.preview_round_canvas = self.create_preview_chart("返稿轮次分布")
        chart_row.addWidget(self.preview_round_card, 1)

        layout.addLayout(chart_row)

        self.preview_confirm_card, self.preview_confirm_fig, self.preview_confirm_canvas = self.create_wide_preview_chart("客户确认周期 TOP")
        layout.addWidget(self.preview_confirm_card)

        self.preview_review_card, self.preview_review_fig, self.preview_review_canvas = self.create_wide_preview_chart("复盘类型分布")
        layout.addWidget(self.preview_review_card)

        table_title = SubtitleLabel("📋 归档数据明细")
        layout.addWidget(table_title)

        self.export_table = TableWidget()
        self.export_table.setColumnCount(12)
        self.export_table.setHorizontalHeaderLabels([
            "项目编号", "项目名称", "客户名称", "配音员",
            "交付文件", "交付版本", "交付日期", "客户确认",
            "返稿轮次", "复盘类型", "复盘结论", "归档时间"
        ])
        self.export_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.export_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.export_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.export_table.verticalHeader().setVisible(False)
        self.export_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.export_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.export_table.setAlternatingRowColors(True)

        layout.addWidget(self.export_table, 1)
        return widget

    def create_preview_chart(self, title):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        title_label = SubtitleLabel(title)
        layout.addWidget(title_label)

        figure = Figure(figsize=(4, 3), dpi=100, facecolor='white')
        canvas = FigureCanvas(figure)
        canvas.setStyleSheet("background-color: white;")
        layout.addWidget(canvas)

        return card, figure, canvas

    def create_wide_preview_chart(self, title):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        title_label = SubtitleLabel(title)
        layout.addWidget(title_label)

        figure = Figure(figsize=(8, 3), dpi=100, facecolor='white')
        canvas = FigureCanvas(figure)
        canvas.setStyleSheet("background-color: white;")
        layout.addWidget(canvas)

        return card, figure, canvas

    def create_summary_card(self):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QHBoxLayout(card)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        self.export_summary_widgets = {}
        stats_config = [
            ("total_archived", "已归档项目", "#0078D4"),
            ("confirmed_count", "客户已确认", "#2ECC71"),
            ("unconfirmed_count", "客户未确认", "#F39C12"),
            ("avg_confirm_days", "平均确认(天)", "#9B59B6"),
            ("avg_round", "平均返稿轮次", "#E74C3C"),
        ]

        for key, label, color in stats_config:
            stat_widget = QWidget()
            stat_widget.setStyleSheet("background-color: transparent;")
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(5)
            stat_layout.setAlignment(Qt.AlignCenter)

            value_label = QLabel("-")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color}; background-color: transparent;")

            label_label = QLabel(label)
            label_label.setAlignment(Qt.AlignCenter)
            label_label.setStyleSheet("font-size: 12px; color: #666; background-color: transparent;")

            stat_layout.addWidget(value_label)
            stat_layout.addWidget(label_label)
            layout.addWidget(stat_widget)

            self.export_summary_widgets[key] = value_label

        return card

    def load_templates(self):
        templates = database.get_all_archive_templates()
        self.tpl_table.setRowCount(len(templates))
        self.tpl_count_label.setText(f"共 {len(templates)} 个模板")

        for row, tpl in enumerate(templates):
            self.tpl_table.setItem(row, 0, QTableWidgetItem(str(tpl['id'])))
            self.tpl_table.setItem(row, 1, QTableWidgetItem(tpl['template_name']))
            self.tpl_table.setItem(row, 2, QTableWidgetItem(tpl.get('client_name') or '通用'))
            self.tpl_table.setItem(row, 3, QTableWidgetItem(tpl.get('project_type') or '-'))
            rule = tpl.get('delivery_file_rule') or '-'
            if len(rule) > 30:
                rule = rule[:30] + '...'
            self.tpl_table.setItem(row, 4, QTableWidgetItem(rule))
            self.tpl_table.setItem(row, 5, QTableWidgetItem(tpl.get('delivery_version_rule') or '-'))
            self.tpl_table.setItem(row, 6, QTableWidgetItem(tpl.get('review_type') or '-'))
            proc = tpl.get('confirm_process') or '-'
            if len(proc) > 25:
                proc = proc[:25] + '...'
            self.tpl_table.setItem(row, 7, QTableWidgetItem(proc))
            default_item = QTableWidgetItem("★ 默认" if tpl.get('is_default') else '')
            if tpl.get('is_default'):
                default_item.setForeground(QColor('#F39C12'))
                default_font = default_item.font()
                default_font.setBold(True)
                default_item.setFont(default_font)
            default_item.setTextAlignment(Qt.AlignCenter)
            self.tpl_table.setItem(row, 8, default_item)

    def load_export_filters(self):
        clients = database.get_all_clients()
        self.export_client_combo.clear()
        self.export_client_combo.addItem("全部")
        for c in clients:
            self.export_client_combo.addItem(c)

        actors = database.get_all_voice_actors()
        self.export_actor_combo.clear()
        self.export_actor_combo.addItem("全部")
        for a in actors:
            self.export_actor_combo.addItem(a)

    def on_export_filter_changed(self):
        self.load_export_data()

    def get_export_params(self):
        return {
            'start_date': self.export_date_start.date().toString("yyyy-MM-dd"),
            'end_date': self.export_date_end.date().toString("yyyy-MM-dd"),
            'client_filter': self.export_client_combo.currentText(),
            'actor_filter': self.export_actor_combo.currentText()
        }

    def load_export_data(self):
        params = self.get_export_params()
        archives = database.get_archived_projects(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        self._current_archives = archives
        self.export_count_label.setText(f"当前筛选共 {len(archives)} 条归档记录")
        self.export_table.setRowCount(len(archives))

        for row, arc in enumerate(archives):
            self.export_table.setItem(row, 0, QTableWidgetItem(arc['project_no']))
            self.export_table.setItem(row, 1, QTableWidgetItem(arc['project_name']))
            self.export_table.setItem(row, 2, QTableWidgetItem(arc['client_name']))
            self.export_table.setItem(row, 3, QTableWidgetItem(arc['voice_actor']))
            self.export_table.setItem(row, 4, QTableWidgetItem(arc['delivery_file'] or '-'))
            self.export_table.setItem(row, 5, QTableWidgetItem(arc['delivery_version'] or '-'))
            self.export_table.setItem(row, 6, QTableWidgetItem(arc['delivery_date'] or '-'))
            confirmed_text = "已确认" if arc['client_confirmed'] else "未确认"
            confirmed_item = QTableWidgetItem(confirmed_text)
            confirmed_item.setForeground(QColor('#2ECC71') if arc['client_confirmed'] else QColor('#F39C12'))
            self.export_table.setItem(row, 7, confirmed_item)
            self.export_table.setItem(row, 8, QTableWidgetItem(str(arc['max_round'])))
            self.export_table.setItem(row, 9, QTableWidgetItem(arc.get('review_type') or '未分类'))
            conclusion = arc['review_conclusion'] or '-'
            if len(conclusion) > 30:
                conclusion = conclusion[:30] + '...'
            self.export_table.setItem(row, 10, QTableWidgetItem(conclusion))
            archived_at = arc.get('archived_at', '') or ''
            if archived_at and ' ' in archived_at:
                archived_at = archived_at.split(' ')[0]
            self.export_table.setItem(row, 11, QTableWidgetItem(archived_at or '-'))

        total = len(archives)
        confirmed = sum(1 for a in archives if a['client_confirmed'])
        unconfirmed = total - confirmed
        avg_round = (sum(a['max_round'] for a in archives) / total) if total > 0 else 0

        confirmed_with_date = [a for a in archives if a['client_confirmed'] and a['client_confirm_date'] and a['delivery_date']]
        if confirmed_with_date:
            total_days = 0
            for a in confirmed_with_date:
                try:
                    d1 = datetime.strptime(a['delivery_date'], "%Y-%m-%d")
                    d2 = datetime.strptime(a['client_confirm_date'], "%Y-%m-%d")
                    total_days += (d2 - d1).days
                except:
                    pass
            avg_days = total_days / len(confirmed_with_date)
        else:
            avg_days = 0

        self.export_summary_widgets['total_archived'].setText(str(total))
        self.export_summary_widgets['confirmed_count'].setText(str(confirmed))
        self.export_summary_widgets['unconfirmed_count'].setText(str(unconfirmed))
        self.export_summary_widgets['avg_confirm_days'].setText(f"{avg_days:.1f}")
        self.export_summary_widgets['avg_round'].setText(f"{avg_round:.1f}")

        self.update_preview_charts(params)

    def update_preview_charts(self, params):
        self.plot_preview_completion(params)
        self.plot_preview_round(params)
        self.plot_preview_confirm(params)
        self.plot_preview_review(params)

    def plot_preview_completion(self, params):
        self.preview_completion_fig.clear()
        ax = self.preview_completion_fig.add_subplot(111)
        ax.set_facecolor('white')

        rate_info = database.get_archive_completion_rate(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        total = rate_info['total']
        archived = rate_info['archived']
        unarchived = total - archived

        if total == 0:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=12, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            values = [archived, max(unarchived, 0)]
            labels = [f'已归档\n{archived}', f'未归档\n{max(unarchived, 0)}']
            colors = ['#2ECC71', '#E0E0E0']

            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.80
            )

            for text in texts:
                text.set_fontsize(9)
                text.set_color('#333')
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_fontweight('bold')

            centre_circle = plt.Circle((0, 0), 0.60, fc='white')
            ax.add_artist(centre_circle)

            ax.text(0, 0.05, f'完成率\n{rate_info["rate"]:.1f}%', ha='center', va='center',
                     fontsize=10, color='#2ECC71', fontweight='bold')

        self.preview_completion_fig.tight_layout()
        self.preview_completion_canvas.draw()

    def plot_preview_round(self, params):
        self.preview_round_fig.clear()
        ax = self.preview_round_fig.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_revision_round_distribution(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=12, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            labels = [f"{int(r)}轮" for r in df['round_num']]
            values = df['count'].astype(int).tolist()
            colors = ['#2ECC71', '#3498DB', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']

            bars = ax.bar(labels, values, color=colors[:len(labels)])

            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f'{int(height)}', ha='center', va='bottom', fontsize=9, color='#333')

            ax.set_xlabel('返稿轮次', color='#333', fontsize=9)
            ax.set_ylabel('项目数', color='#333', fontsize=9)
            ax.tick_params(axis='x', colors='#333', labelsize=8)
            ax.tick_params(axis='y', colors='#333', labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', alpha=0.3, color='#ccc')

        self.preview_round_fig.tight_layout()
        self.preview_round_canvas.draw()

    def plot_preview_confirm(self, params):
        self.preview_confirm_fig.clear()
        ax = self.preview_confirm_fig.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_client_confirm_cycle_statistics(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=12, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            df_top = df.head(8)
            colors = plt.cm.Blues([(v - df_top['avg_confirm_days'].min() + 1) /
                                    (df_top['avg_confirm_days'].max() - df_top['avg_confirm_days'].min() + 1)
                                    for v in df_top['avg_confirm_days']])

            bars = ax.barh(df_top['client_name'][::-1], df_top['avg_confirm_days'][::-1],
                           color=colors[::-1])

            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2,
                        f' {width:.1f}天', ha='left', va='center', fontsize=8, color='#333')

            ax.set_xlabel('平均确认天数', color='#333', fontsize=9)
            ax.tick_params(axis='x', colors='#333', labelsize=8)
            ax.tick_params(axis='y', colors='#333', labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')

        self.preview_confirm_fig.tight_layout()
        self.preview_confirm_canvas.draw()

    def plot_preview_review(self, params):
        self.preview_review_fig.clear()
        ax = self.preview_review_fig.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_archive_review_summary(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty or df['count'].sum() == 0:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=12, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            type_colors = {
                '质量问题': '#E74C3C', '客户需求变更': '#F39C12',
                '沟通问题': '#9B59B6', '流程问题': '#3498DB',
                '表现优秀': '#2ECC71', '其他': '#95A5A6',
                '未分类': '#BDC3C7'
            }

            df_sorted = df.sort_values('count', ascending=True)
            colors = [type_colors.get(rt, '#3498DB') for rt in df_sorted['review_type']]

            bars = ax.barh(df_sorted['review_type'], df_sorted['count'], color=colors)

            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2,
                        f' {int(width)}', ha='left', va='center', fontsize=8, color='#333')

            ax.set_xlabel('项目数', color='#333', fontsize=9)
            ax.tick_params(axis='x', colors='#333', labelsize=8)
            ax.tick_params(axis='y', colors='#333', labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')

        self.preview_review_fig.tight_layout()
        self.preview_review_canvas.draw()

    def get_selected_template_id(self):
        current_row = self.tpl_table.currentRow()
        if current_row >= 0:
            item = self.tpl_table.item(current_row, 0)
            if item:
                return int(item.text())
        return None

    def on_add_template(self):
        dialog = TemplateDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                database.add_archive_template(**data)
                self.show_success("模板创建成功")
                self.load_templates()
            except ValueError as e:
                self.show_warning(str(e))

    def on_edit_template(self):
        tpl_id = self.get_selected_template_id()
        if not tpl_id:
            self.show_warning("请先选择一个模板")
            return
        dialog = TemplateDialog(self, template_id=tpl_id)
        if dialog.exec():
            data = dialog.get_data()
            try:
                database.update_archive_template(tpl_id, **data)
                self.show_success("模板更新成功")
                self.load_templates()
            except ValueError as e:
                self.show_warning(str(e))

    def on_delete_template(self):
        tpl_id = self.get_selected_template_id()
        if not tpl_id:
            self.show_warning("请先选择一个模板")
            return
        tpl = database.get_archive_template_by_id(tpl_id)
        tpl_name = tpl['template_name'] if tpl else '该模板'
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板「{tpl_name}」吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            database.delete_archive_template(tpl_id)
            self.show_success("删除成功")
            self.load_templates()

    def _build_export_dataframes(self, params):
        archives = database.get_archived_projects(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if not archives:
            return None, None, None, None

        df_data = []
        for a in archives:
            df_data.append({
                '项目编号': a['project_no'],
                '项目名称': a['project_name'],
                '客户名称': a['client_name'],
                '配音员': a['voice_actor'],
                '交付文件': a['delivery_file'] or '',
                '交付版本': a['delivery_version'] or '',
                '交付日期': a['delivery_date'] or '',
                '客户确认': '已确认' if a['client_confirmed'] else '未确认',
                '确认日期': a['client_confirm_date'] or '',
                '返稿轮次': a['max_round'],
                '复盘类型': a.get('review_type') or '未分类',
                '复盘结论': a['review_conclusion'] or '',
                '归档时间': a.get('archived_at', '') or ''
            })
        df_archives = pd.DataFrame(df_data)

        total = len(archives)
        confirmed = sum(1 for a in archives if a['client_confirmed'])
        unconfirmed = total - confirmed
        avg_round = (sum(a['max_round'] for a in archives) / total) if total > 0 else 0
        confirmed_with_date = [a for a in archives if a['client_confirmed'] and a['client_confirm_date'] and a['delivery_date']]
        if confirmed_with_date:
            total_days = 0
            for a in confirmed_with_date:
                try:
                    d1 = datetime.strptime(a['delivery_date'], "%Y-%m-%d")
                    d2 = datetime.strptime(a['client_confirm_date'], "%Y-%m-%d")
                    total_days += (d2 - d1).days
                except:
                    pass
            avg_days = total_days / len(confirmed_with_date)
        else:
            avg_days = 0

        df_summary = pd.DataFrame([{
            '统计项': '已归档项目数',
            '数值': total
        }, {
            '统计项': '客户已确认数',
            '数值': confirmed
        }, {
            '统计项': '客户未确认数',
            '数值': unconfirmed
        }, {
            '统计项': '平均确认周期(天)',
            '数值': round(avg_days, 2)
        }, {
            '统计项': '平均返稿轮次',
            '数值': round(avg_round, 2)
        }])

        df_review = database.get_archive_review_summary(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        if df_review is not None and not df_review.empty:
            df_review = df_review.rename(columns={'review_type': '复盘类型', 'count': '项目数'})

        df_round = database.get_revision_round_distribution(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        if df_round is not None and not df_round.empty:
            df_round = df_round.rename(columns={'round_num': '返稿轮次', 'count': '项目数'})
            df_round['返稿轮次'] = df_round['返稿轮次'].astype(int).astype(str) + '轮'

        return df_archives, df_summary, df_review, df_round

    def on_export_excel(self):
        params = self.get_export_params()
        df_archives, df_summary, df_review, df_round = self._build_export_dataframes(params)

        if df_archives is None or df_archives.empty:
            self.show_warning("当前筛选条件下没有数据可导出")
            return

        default_name = f"归档报表_{params['start_date']}_{params['end_date']}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel 报表", default_name, "Excel 文件 (*.xlsx)"
        )
        if not file_path:
            return

        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df_archives.to_excel(writer, sheet_name='归档明细', index=False)
                df_summary.to_excel(writer, sheet_name='汇总统计', index=False)
                if df_review is not None and not df_review.empty:
                    df_review.to_excel(writer, sheet_name='复盘统计', index=False)
                if df_round is not None and not df_round.empty:
                    df_round.to_excel(writer, sheet_name='返稿轮次统计', index=False)
            self.show_success(f"Excel 已导出：{os.path.basename(file_path)}")
        except ImportError:
            self.show_warning("缺少 openpyxl 依赖，请先安装：pip install openpyxl")
        except Exception as e:
            self.show_warning(f"导出失败：{str(e)}")

    def _render_chart_figure(self, params):
        fig = Figure(figsize=(14, 10), dpi=150, facecolor='white')

        df_summary = database.get_archive_completion_rate(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.set_facecolor('white')
        if df_summary and df_summary.get('total', 0) > 0:
            archived = df_summary.get('archived', 0)
            unarchived = df_summary.get('total', 0) - archived
            values = [archived, max(unarchived, 0)]
            labels = [f'已归档\n{archived}', f'未归档\n{max(unarchived, 0)}']
            colors = ['#2ECC71', '#E0E0E0']
            wedges, texts, autotexts = ax1.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.80
            )
            for t in texts:
                t.set_fontsize(9)
            for at in autotexts:
                at.set_fontsize(8)
                at.set_fontweight('bold')
            centre_circle = plt.Circle((0, 0), 0.60, fc='white')
            ax1.add_artist(centre_circle)
            ax1.text(0, 0.05, f'完成率\n{df_summary["rate"]:.1f}%',
                     ha='center', va='center', fontsize=10, color='#2ECC71', fontweight='bold')
        else:
            ax1.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                     fontsize=12, color='gray', transform=ax1.transAxes)
            ax1.set_axis_off()
        ax1.set_title('归档完成率', fontsize=11, fontweight='bold', color='#333')

        df_round = database.get_revision_round_distribution(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.set_facecolor('white')
        if df_round is not None and not df_round.empty:
            labels = [f"{int(r)}轮" for r in df_round['round_num']]
            values = df_round['count'].astype(int).tolist()
            colors = ['#2ECC71', '#3498DB', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']
            bars = ax2.bar(labels, values, color=colors[:len(labels)])
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax2.text(bar.get_x() + bar.get_width() / 2, h,
                             f'{int(h)}', ha='center', va='bottom', fontsize=9)
            ax2.set_xlabel('返稿轮次', color='#333', fontsize=9)
            ax2.set_ylabel('项目数', color='#333', fontsize=9)
            ax2.tick_params(axis='x', labelsize=8)
            ax2.tick_params(axis='y', labelsize=8)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.grid(axis='y', alpha=0.3, color='#ccc')
        else:
            ax2.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                     fontsize=12, color='gray', transform=ax2.transAxes)
            ax2.set_axis_off()
        ax2.set_title('返稿轮次分布', fontsize=11, fontweight='bold', color='#333')

        df_confirm = database.get_client_confirm_cycle_statistics(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        ax3 = fig.add_subplot(2, 2, 3)
        ax3.set_facecolor('white')
        if df_confirm is not None and not df_confirm.empty:
            df_top = df_confirm.head(8)
            norm = plt.Normalize(df_top['avg_confirm_days'].min(), df_top['avg_confirm_days'].max() + 1)
            colors = plt.cm.Blues(norm(df_top['avg_confirm_days']))
            bars = ax3.barh(df_top['client_name'][::-1], df_top['avg_confirm_days'][::-1], color=colors[::-1])
            for bar in bars:
                w = bar.get_width()
                ax3.text(w, bar.get_y() + bar.get_height() / 2,
                         f' {w:.1f}天', ha='left', va='center', fontsize=8)
            ax3.set_xlabel('平均确认天数', color='#333', fontsize=9)
            ax3.tick_params(axis='x', labelsize=8)
            ax3.tick_params(axis='y', labelsize=8)
            ax3.spines['top'].set_visible(False)
            ax3.spines['right'].set_visible(False)
            ax3.grid(axis='x', alpha=0.3, color='#ccc')
        else:
            ax3.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                     fontsize=12, color='gray', transform=ax3.transAxes)
            ax3.set_axis_off()
        ax3.set_title('客户确认周期 TOP', fontsize=11, fontweight='bold', color='#333')

        df_review = database.get_archive_review_summary(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        ax4 = fig.add_subplot(2, 2, 4)
        ax4.set_facecolor('white')
        if df_review is not None and not df_review.empty and df_review['count'].sum() > 0:
            type_colors = {
                '质量问题': '#E74C3C', '客户需求变更': '#F39C12',
                '沟通问题': '#9B59B6', '流程问题': '#3498DB',
                '表现优秀': '#2ECC71', '其他': '#95A5A6',
                '未分类': '#BDC3C7'
            }
            df_sorted = df_review.sort_values('count', ascending=True)
            colors = [type_colors.get(rt, '#3498DB') for rt in df_sorted['review_type']]
            bars = ax4.barh(df_sorted['review_type'], df_sorted['count'], color=colors)
            for bar in bars:
                w = bar.get_width()
                ax4.text(w, bar.get_y() + bar.get_height() / 2,
                         f' {int(w)}', ha='left', va='center', fontsize=8)
            ax4.set_xlabel('项目数', color='#333', fontsize=9)
            ax4.tick_params(axis='x', labelsize=8)
            ax4.tick_params(axis='y', labelsize=8)
            ax4.spines['top'].set_visible(False)
            ax4.spines['right'].set_visible(False)
            ax4.grid(axis='x', alpha=0.3, color='#ccc')
        else:
            ax4.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                     fontsize=12, color='gray', transform=ax4.transAxes)
            ax4.set_axis_off()
        ax4.set_title('复盘类型分布', fontsize=11, fontweight='bold', color='#333')

        fig.suptitle(
            f'归档数据统计报表  ({params["start_date"]} ~ {params["end_date"]})',
            fontsize=14, fontweight='bold', color='#333'
        )
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        return fig

    def on_export_charts(self):
        params = self.get_export_params()
        default_name = f"统计图表_{params['start_date']}_{params['end_date']}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出统计图表", default_name, "PNG 图片 (*.png)"
        )
        if not file_path:
            return

        try:
            fig = self._render_chart_figure(params)
            fig.savefig(file_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.show_success(f"图表已导出：{os.path.basename(file_path)}")
        except Exception as e:
            self.show_warning(f"导出失败：{str(e)}")

    def on_export_all(self):
        params = self.get_export_params()
        df_archives, df_summary, df_review, df_round = self._build_export_dataframes(params)
        if df_archives is None or df_archives.empty:
            self.show_warning("当前筛选条件下没有数据可导出")
            return

        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not dir_path:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"归档导出_{params['start_date']}_{params['end_date']}_{timestamp}"
        excel_path = os.path.join(dir_path, f"{base_name}.xlsx")
        chart_path = os.path.join(dir_path, f"{base_name}_图表.png")

        success_count = 0
        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_archives.to_excel(writer, sheet_name='归档明细', index=False)
                df_summary.to_excel(writer, sheet_name='汇总统计', index=False)
                if df_review is not None and not df_review.empty:
                    df_review.to_excel(writer, sheet_name='复盘统计', index=False)
                if df_round is not None and not df_round.empty:
                    df_round.to_excel(writer, sheet_name='返稿轮次统计', index=False)
            success_count += 1
        except ImportError:
            self.show_warning("缺少 openpyxl 依赖，Excel 导出跳过")
        except Exception as e:
            self.show_warning(f"Excel 导出失败：{str(e)}")

        try:
            fig = self._render_chart_figure(params)
            fig.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            success_count += 1
        except Exception as e:
            self.show_warning(f"图表导出失败：{str(e)}")

        if success_count > 0:
            self.show_success(f"已成功导出 {success_count} 个文件到：{dir_path}")
        else:
            self.show_warning("未成功导出任何文件")

    def show_warning(self, message):
        InfoBar.warning(
            title="提示", content=message,
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def show_success(self, message):
        InfoBar.success(
            title="成功", content=message,
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def refresh(self):
        self.load_templates()
        self.load_export_filters()
        self.load_export_data()
