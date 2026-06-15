from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QScrollArea, QFrame, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QDialog,
                               QFormLayout, QLineEdit, QComboBox, QDateEdit,
                               QSpinBox, QTextEdit, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from qfluentwidgets import (CardWidget, TableWidget, ComboBox,
                            SubtitleLabel, TitleLabel, DateEdit,
                            PrimaryPushButton, PushButton, InfoBar, InfoBarPosition)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams

import database

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False


class ArchiveDialog(QDialog):
    def __init__(self, parent=None, archive_id=None):
        super().__init__(parent)
        self.archive_id = archive_id
        self.setWindowTitle("编辑归档" if archive_id else "新增归档")
        self.setMinimumWidth(500)
        self.init_ui()
        if archive_id:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.project_combo = QComboBox()
        self._load_projects()
        form.addRow("选择项目*：", self.project_combo)

        self.delivery_file_edit = QLineEdit()
        self.delivery_file_edit.setPlaceholderText("如：final_v2.wav")
        form.addRow("交付文件：", self.delivery_file_edit)

        self.delivery_version_edit = QLineEdit()
        self.delivery_version_edit.setPlaceholderText("如：v2.0")
        form.addRow("交付版本：", self.delivery_version_edit)

        self.delivery_date_edit = QDateEdit()
        self.delivery_date_edit.setCalendarPopup(True)
        self.delivery_date_edit.setDate(QDate.currentDate())
        self.delivery_date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("交付日期*：", self.delivery_date_edit)

        self.client_confirmed_combo = QComboBox()
        self.client_confirmed_combo.addItems(["未确认", "已确认"])
        form.addRow("客户确认：", self.client_confirmed_combo)

        self.client_confirm_date_edit = QDateEdit()
        self.client_confirm_date_edit.setCalendarPopup(True)
        self.client_confirm_date_edit.setDate(QDate.currentDate())
        self.client_confirm_date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("客户确认日期：", self.client_confirm_date_edit)

        self.review_type_combo = QComboBox()
        self.review_type_combo.addItems(['', '质量问题', '客户需求变更', '沟通问题', '流程问题', '表现优秀', '其他'])
        form.addRow("复盘类型：", self.review_type_combo)

        self.review_conclusion_edit = QTextEdit()
        self.review_conclusion_edit.setMaximumHeight(100)
        self.review_conclusion_edit.setPlaceholderText("如：项目顺利交付，客户满意度高，返稿主要因发音问题...")
        form.addRow("复盘结论：", self.review_conclusion_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_projects(self):
        projects = database.get_all_projects()
        completed = [p for p in projects if p['revision_status'] in ('已完成', '已验收')]
        self._project_data = completed
        self.project_combo.clear()
        for p in completed:
            existing = database.get_archive_by_project_id(p['id'])
            if existing and (self.archive_id is None or existing['id'] != self.archive_id):
                continue
            self.project_combo.addItem(f"{p['project_no']} - {p['project_name']}", p['id'])

    def load_data(self):
        archive = database.get_archive_by_id(self.archive_id)
        if not archive:
            return
        idx = self.project_combo.findData(archive['project_id'])
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)
            self.project_combo.setEnabled(False)
        self.delivery_file_edit.setText(archive['delivery_file'] or '')
        self.delivery_version_edit.setText(archive['delivery_version'] or '')
        if archive['delivery_date']:
            self.delivery_date_edit.setDate(QDate.fromString(archive['delivery_date'], "yyyy-MM-dd"))
        self.client_confirmed_combo.setCurrentIndex(archive['client_confirmed'])
        if archive['client_confirm_date']:
            self.client_confirm_date_edit.setDate(QDate.fromString(archive['client_confirm_date'], "yyyy-MM-dd"))
        review_type = archive.get('review_type', '') or ''
        idx_rt = self.review_type_combo.findText(review_type)
        if idx_rt >= 0:
            self.review_type_combo.setCurrentIndex(idx_rt)
        self.review_conclusion_edit.setPlainText(archive['review_conclusion'] or '')

    def validate_and_accept(self):
        if self.project_combo.currentData() is None:
            InfoBar.warning(title="提示", content="请选择一个可归档的项目",
                            orient=Qt.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP, duration=2000, parent=self)
            return
        self.accept()

    def get_data(self):
        return {
            'project_id': self.project_combo.currentData(),
            'delivery_file': self.delivery_file_edit.text().strip(),
            'delivery_version': self.delivery_version_edit.text().strip(),
            'delivery_date': self.delivery_date_edit.date().toString("yyyy-MM-dd"),
            'client_confirmed': self.client_confirmed_combo.currentIndex(),
            'client_confirm_date': self.client_confirm_date_edit.date().toString("yyyy-MM-dd") if self.client_confirmed_combo.currentIndex() == 1 else '',
            'review_type': self.review_type_combo.currentText().strip(),
            'review_conclusion': self.review_conclusion_edit.toPlainText().strip(),
        }


class ArchivePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ArchivePage")

        self.setStyleSheet("""
            ArchivePage { background-color: white; }
            QScrollArea { background-color: white; border: none; }
            QWidget#contentWidget { background-color: white; }
            QLabel { color: #333; }
        """)

        self.init_ui()
        self.load_filters()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = TitleLabel("交付归档与复盘报告")
        layout.addWidget(title)

        filter_card = CardWidget()
        filter_card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 12, 15, 12)
        filter_layout.setSpacing(15)

        date_start_label = QLabel("开始日期：")
        date_start_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(date_start_label)

        self.date_start = DateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate(2000, 1, 1))
        self.date_start.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.date_start)

        date_end_label = QLabel("结束日期：")
        date_end_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(date_end_label)

        self.date_end = DateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.date_end)

        client_label = QLabel("客户：")
        client_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(client_label)

        self.client_combo = ComboBox()
        self.client_combo.setMinimumWidth(130)
        self.client_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.client_combo)

        actor_label = QLabel("配音员：")
        actor_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(actor_label)

        self.actor_combo = ComboBox()
        self.actor_combo.setMinimumWidth(130)
        self.actor_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.actor_combo)

        filter_layout.addStretch()
        layout.addWidget(filter_card)

        btn_card = CardWidget()
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        btn_layout.setSpacing(10)

        self.add_btn = PrimaryPushButton("新增归档")
        self.add_btn.clicked.connect(self.on_add_archive)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = PushButton("编辑归档")
        self.edit_btn.clicked.connect(self.on_edit_archive)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = PushButton("删除归档")
        self.delete_btn.clicked.connect(self.on_delete_archive)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.stats_label = QLabel("共 0 条归档记录")
        self.stats_label.setStyleSheet("color: #666; font-size: 13px;")
        btn_layout.addWidget(self.stats_label)

        layout.addWidget(btn_card)

        self.summary_card = self.create_summary_card()
        layout.addWidget(self.summary_card)

        table_card = CardWidget()
        table_card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)

        table_title = SubtitleLabel("归档项目列表")
        table_layout.addWidget(table_title)

        self.table = TableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "归档ID", "项目编号", "项目名称", "客户名称", "配音员",
            "交付文件", "交付版本", "交付日期", "客户确认", "确认日期",
            "返稿轮次", "复盘类型", "复盘结论", "归档时间"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnHidden(0, True)
        self.table.setAlternatingRowColors(True)

        table_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: white; }")

        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_widget.setStyleSheet("#contentWidget { background-color: white; }")

        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(15)

        self.completion_chart_card, self.completion_figure, self.completion_canvas = self.create_chart_card("项目完成率")
        chart_row.addWidget(self.completion_chart_card, 1)

        self.round_chart_card, self.round_figure, self.round_canvas = self.create_chart_card("返稿轮次分布")
        chart_row.addWidget(self.round_chart_card, 1)

        content_layout.addLayout(chart_row)

        self.confirm_cycle_card, self.confirm_cycle_figure, self.confirm_cycle_canvas = self.create_wide_chart_card("客户确认周期")
        content_layout.addWidget(self.confirm_cycle_card)

        self.review_chart_card, self.review_figure, self.review_canvas = self.create_wide_chart_card("归档项目复盘摘要")
        content_layout.addWidget(self.review_chart_card)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_summary_card(self):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QHBoxLayout(card)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        self.summary_widgets = {}
        stats_config = [
            ("total_archived", "已归档项目", "#0078D4"),
            ("completion_rate", "归档完成率", "#2ECC71"),
            ("confirmed_count", "客户已确认", "#1ABC9C"),
            ("unconfirmed_count", "客户未确认", "#F39C12"),
            ("avg_confirm_days", "平均确认周期(天)", "#9B59B6"),
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

            self.summary_widgets[key] = value_label

        return card

    def create_chart_card(self, title):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        title_label = SubtitleLabel(title)
        layout.addWidget(title_label)

        figure = Figure(figsize=(4, 3.5), dpi=100, facecolor='white')
        canvas = FigureCanvas(figure)
        canvas.setStyleSheet("background-color: white;")
        layout.addWidget(canvas)

        return card, figure, canvas

    def create_wide_chart_card(self, title):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        title_label = SubtitleLabel(title)
        layout.addWidget(title_label)

        figure = Figure(figsize=(8, 3.5), dpi=100, facecolor='white')
        canvas = FigureCanvas(figure)
        canvas.setStyleSheet("background-color: white;")
        layout.addWidget(canvas)

        return card, figure, canvas

    def load_filters(self):
        clients = database.get_all_clients()
        self.client_combo.clear()
        self.client_combo.addItem("全部")
        for client in clients:
            self.client_combo.addItem(client)

        actors = database.get_all_voice_actors()
        self.actor_combo.clear()
        self.actor_combo.addItem("全部")
        for actor in actors:
            self.actor_combo.addItem(actor)

    def on_filter_changed(self):
        self.load_data()

    def get_filter_params(self):
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")
        client_filter = self.client_combo.currentText()
        actor_filter = self.actor_combo.currentText()

        return {
            'start_date': start_date,
            'end_date': end_date,
            'client_filter': client_filter,
            'actor_filter': actor_filter
        }

    def load_data(self):
        params = self.get_filter_params()
        self.load_archives(params)
        self.load_summary(params)
        self.plot_completion_chart(params)
        self.plot_round_chart(params)
        self.plot_confirm_cycle_chart(params)
        self.plot_review_chart(params)

    def load_archives(self, params):
        archives = database.get_archived_projects(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        self.table.setRowCount(len(archives))
        self.stats_label.setText(f"共 {len(archives)} 条归档记录")

        for row, arc in enumerate(archives):
            self.table.setItem(row, 0, QTableWidgetItem(str(arc['archive_id'])))
            self.table.setItem(row, 1, QTableWidgetItem(arc['project_no']))
            self.table.setItem(row, 2, QTableWidgetItem(arc['project_name']))
            self.table.setItem(row, 3, QTableWidgetItem(arc['client_name']))
            self.table.setItem(row, 4, QTableWidgetItem(arc['voice_actor']))
            self.table.setItem(row, 5, QTableWidgetItem(arc['delivery_file'] or '-'))
            self.table.setItem(row, 6, QTableWidgetItem(arc['delivery_version'] or '-'))
            self.table.setItem(row, 7, QTableWidgetItem(arc['delivery_date'] or '-'))

            confirmed_text = "已确认" if arc['client_confirmed'] else "未确认"
            confirmed_item = QTableWidgetItem(confirmed_text)
            confirmed_item.setForeground(QColor('#2ECC71') if arc['client_confirmed'] else QColor('#F39C12'))
            self.table.setItem(row, 8, confirmed_item)

            self.table.setItem(row, 9, QTableWidgetItem(arc['client_confirm_date'] or '-'))

            round_item = QTableWidgetItem(str(arc['max_round']))
            if arc['max_round'] >= 3:
                round_item.setForeground(QColor('#E74C3C'))
            elif arc['max_round'] >= 2:
                round_item.setForeground(QColor('#F39C12'))
            self.table.setItem(row, 10, round_item)

            review_type = arc.get('review_type', '') or '未分类'
            type_colors = {
                '质量问题': '#E74C3C', '客户需求变更': '#F39C12',
                '沟通问题': '#9B59B6', '流程问题': '#3498DB',
                '表现优秀': '#2ECC71', '其他': '#95A5A6',
                '未分类': '#BDC3C7'
            }
            type_item = QTableWidgetItem(review_type)
            type_item.setForeground(QColor(type_colors.get(review_type, '#333')))
            self.table.setItem(row, 11, type_item)

            conclusion = arc['review_conclusion'] or '-'
            if len(conclusion) > 30:
                conclusion = conclusion[:30] + '...'
            self.table.setItem(row, 12, QTableWidgetItem(conclusion))

            archived_at = arc.get('archived_at', '') or ''
            if archived_at and ' ' in archived_at:
                archived_at = archived_at.split(' ')[0]
            self.table.setItem(row, 13, QTableWidgetItem(archived_at or '-'))

    def load_summary(self, params):
        archives = database.get_archived_projects(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        rate_info = database.get_archive_completion_rate(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        total_archived = len(archives)
        confirmed_count = sum(1 for a in archives if a['client_confirmed'])
        unconfirmed_count = total_archived - confirmed_count
        avg_round = (sum(a['max_round'] for a in archives) / total_archived) if total_archived > 0 else 0

        confirmed_with_date = [a for a in archives if a['client_confirmed'] and a['client_confirm_date'] and a['delivery_date']]
        if confirmed_with_date:
            from datetime import datetime
            total_days = 0
            for a in confirmed_with_date:
                try:
                    d1 = datetime.strptime(a['delivery_date'], "%Y-%m-%d")
                    d2 = datetime.strptime(a['client_confirm_date'], "%Y-%m-%d")
                    total_days += (d2 - d1).days
                except:
                    pass
            avg_confirm_days = total_days / len(confirmed_with_date)
        else:
            avg_confirm_days = 0

        self.summary_widgets['total_archived'].setText(str(total_archived))
        self.summary_widgets['completion_rate'].setText(f"{rate_info['rate']:.1f}%")
        self.summary_widgets['confirmed_count'].setText(str(confirmed_count))
        self.summary_widgets['unconfirmed_count'].setText(str(unconfirmed_count))
        self.summary_widgets['avg_confirm_days'].setText(f"{avg_confirm_days:.1f}")
        self.summary_widgets['avg_round'].setText(f"{avg_round:.1f}")

    def plot_completion_chart(self, params):
        self.completion_figure.clear()
        ax = self.completion_figure.add_subplot(111)
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
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            values = [archived, unarchived]
            labels = [f'已归档\n{archived}', f'未归档\n{unarchived}']
            colors = ['#2ECC71', '#E0E0E0']

            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.80
            )

            for text in texts:
                text.set_fontsize(10)
                text.set_color('#333')
            for autotext in autotexts:
                autotext.set_fontsize(9)
                autotext.set_fontweight('bold')

            centre_circle = plt.Circle((0, 0), 0.60, fc='white')
            ax.add_artist(centre_circle)

            ax.text(0, 0.05, f'完成率\n{rate_info["rate"]:.1f}%', ha='center', va='center',
                    fontsize=12, color='#2ECC71', fontweight='bold')

        self.completion_figure.tight_layout()
        self.completion_canvas.draw()

    def plot_round_chart(self, params):
        self.round_figure.clear()
        ax = self.round_figure.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_revision_round_distribution(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=14, color='gray', transform=ax.transAxes)
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
                            f'{int(height)}', ha='center', va='bottom', fontsize=10, color='#333')

            ax.set_xlabel('返稿轮次', color='#333')
            ax.set_ylabel('项目数', color='#333')
            ax.tick_params(axis='x', colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', alpha=0.3, color='#ccc')

        self.round_figure.tight_layout()
        self.round_canvas.draw()

    def plot_confirm_cycle_chart(self, params):
        self.confirm_cycle_figure.clear()
        ax = self.confirm_cycle_figure.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_client_confirm_cycle_statistics(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            df_top = df.head(10)
            colors = plt.cm.Blues([(v - df_top['avg_confirm_days'].min() + 1) /
                                    (df_top['avg_confirm_days'].max() - df_top['avg_confirm_days'].min() + 1)
                                    for v in df_top['avg_confirm_days']])

            bars = ax.barh(df_top['client_name'][::-1], df_top['avg_confirm_days'][::-1],
                           color=colors[::-1])

            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height() / 2,
                        f' {width:.1f}天', ha='left', va='center', fontsize=9, color='#333')

            ax.set_xlabel('平均确认天数', color='#333')
            ax.tick_params(axis='x', colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')

        self.confirm_cycle_figure.tight_layout()
        self.confirm_cycle_canvas.draw()

    def plot_review_chart(self, params):
        self.review_figure.clear()
        ax = self.review_figure.add_subplot(111)
        ax.set_facecolor('white')

        df = database.get_archive_review_summary(
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )

        if df.empty or df['count'].sum() == 0:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center',
                    fontsize=14, color='gray', transform=ax.transAxes)
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
                        f' {int(width)}', ha='left', va='center', fontsize=9, color='#333')

            ax.set_xlabel('项目数', color='#333')
            ax.tick_params(axis='x', colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')

        self.review_figure.tight_layout()
        self.review_canvas.draw()

    def get_selected_archive_id(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            item = self.table.item(current_row, 0)
            if item:
                return int(item.text())
        return None

    def on_add_archive(self):
        dialog = ArchiveDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data['project_id'] is None:
                return
            try:
                database.add_archive(
                    project_id=data['project_id'],
                    delivery_file=data['delivery_file'],
                    delivery_version=data['delivery_version'],
                    delivery_date=data['delivery_date'],
                    client_confirmed=data['client_confirmed'],
                    client_confirm_date=data['client_confirm_date'],
                    review_type=data['review_type'],
                    review_conclusion=data['review_conclusion']
                )
                self.show_success("归档成功")
                self.load_data()
            except ValueError as e:
                self.show_warning(str(e))

    def on_edit_archive(self):
        archive_id = self.get_selected_archive_id()
        if not archive_id:
            self.show_warning("请先选择一条归档记录")
            return

        dialog = ArchiveDialog(self, archive_id=archive_id)
        if dialog.exec():
            data = dialog.get_data()
            database.update_archive(
                archive_id=archive_id,
                delivery_file=data['delivery_file'],
                delivery_version=data['delivery_version'],
                delivery_date=data['delivery_date'],
                client_confirmed=data['client_confirmed'],
                client_confirm_date=data['client_confirm_date'],
                review_type=data['review_type'],
                review_conclusion=data['review_conclusion']
            )
            self.show_success("更新成功")
            self.load_data()

    def on_delete_archive(self):
        archive_id = self.get_selected_archive_id()
        if not archive_id:
            self.show_warning("请先选择一条归档记录")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该归档记录吗？\n项目数据不会被删除，仅移除归档信息。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            database.delete_archive(archive_id)
            self.show_success("删除成功")
            self.load_data()

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
        self.load_filters()
        self.load_data()
