from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidgetItem, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from qfluentwidgets import (CardWidget, TableWidget, ComboBox, TitleLabel, 
                            SubtitleLabel, InfoBar, InfoBarPosition,
                            PrimaryPushButton)
from project_detail_dialog import ProjectDetailDialog
import database

class VoiceActorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VoiceActorPage")
        self.init_ui()
        self.load_actors()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = TitleLabel("配音员维度")
        layout.addWidget(title)
        
        filter_card = CardWidget()
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(15)
        
        filter_label = SubtitleLabel("选择配音员：")
        filter_layout.addWidget(filter_label)
        
        self.actor_combo = ComboBox()
        self.actor_combo.setMinimumWidth(200)
        self.actor_combo.currentIndexChanged.connect(self.on_actor_changed)
        filter_layout.addWidget(self.actor_combo)
        
        filter_layout.addStretch()
        layout.addWidget(filter_card)
        
        self.summary_card = self.create_summary_card()
        layout.addWidget(self.summary_card)
        
        projects_card = CardWidget()
        projects_layout = QVBoxLayout(projects_card)
        projects_layout.setContentsMargins(15, 15, 15, 15)
        projects_layout.setSpacing(10)
        
        projects_title = SubtitleLabel("项目列表")
        projects_layout.addWidget(projects_title)
        
        self.table = TableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "项目编号", "项目名称", "客户名称", "初稿日期", 
            "返稿状态", "最终结果", "返稿次数"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnHidden(0, True)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        
        projects_layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.view_detail_btn = PrimaryPushButton("查看详情")
        self.view_detail_btn.clicked.connect(self.on_view_detail)
        btn_layout.addWidget(self.view_detail_btn)
        btn_layout.addStretch()
        projects_layout.addLayout(btn_layout)
        
        layout.addWidget(projects_card, 1)
    
    def create_summary_card(self):
        card = CardWidget()
        layout = QHBoxLayout(card)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.stat_widgets = {}
        stats_config = [
            ("total_projects", "总项目数", "#0078D4"),
            ("projects_with_revision", "返稿项目数", "#E74C3C"),
            ("revision_rate", "返稿率", "#F39C12"),
            ("total_revisions", "总返稿次数", "#9B59B6"),
            ("avg_round", "平均返稿轮次", "#1ABC9C"),
            ("urgent_count", "加急次数", "#E67E22"),
        ]
        
        for key, label, color in stats_config:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(5)
            stat_layout.setAlignment(Qt.AlignCenter)
            
            value_label = QLabel("-")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
            
            label_label = QLabel(label)
            label_label.setAlignment(Qt.AlignCenter)
            label_label.setStyleSheet("font-size: 12px; color: #666;")
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(label_label)
            layout.addWidget(stat_widget)
            
            self.stat_widgets[key] = value_label
        
        return card
    
    def load_actors(self):
        actors = database.get_all_voice_actors()
        self.actor_combo.clear()
        self.actor_combo.addItem("全部")
        
        for actor in actors:
            self.actor_combo.addItem(actor)
        
        if self.actor_combo.count() > 0:
            self.actor_combo.setCurrentIndex(0)
    
    def on_actor_changed(self):
        self.load_data()
    
    def load_data(self):
        selected_actor = self.actor_combo.currentText()
        
        if selected_actor == "全部":
            projects = database.get_all_projects()
        else:
            projects = database.get_all_projects(actor_filter=selected_actor)
        
        self.load_summary(selected_actor, projects)
        self.load_projects_table(projects)
    
    def load_summary(self, selected_actor, projects):
        if selected_actor == "全部":
            df = database.get_voice_actor_statistics()
            
            total_projects = int(df['total_projects'].sum()) if not df.empty else 0
            projects_with_revision = int(df['projects_with_revision'].sum()) if not df.empty else 0
            total_revisions = int(df['total_revisions'].sum()) if not df.empty else 0
            urgent_count = int(df['urgent_count'].sum()) if not df.empty else 0
            
            revision_rate = (projects_with_revision / total_projects * 100) if total_projects > 0 else 0
            avg_round = (total_revisions / projects_with_revision) if projects_with_revision > 0 else 0
        else:
            df = database.get_voice_actor_statistics()
            actor_df = df[df['voice_actor'] == selected_actor]
            
            if actor_df.empty:
                total_projects = 0
                projects_with_revision = 0
                total_revisions = 0
                urgent_count = 0
                revision_rate = 0
                avg_round = 0
            else:
                data = actor_df.iloc[0]
                total_projects = int(data['total_projects'])
                projects_with_revision = int(data['projects_with_revision'])
                total_revisions = int(data['total_revisions'])
                urgent_count = int(data['urgent_count']) if not data['urgent_count'] is None else 0
                revision_rate = (projects_with_revision / total_projects * 100) if total_projects > 0 else 0
                avg_round = data['avg_round'] if data['avg_round'] is not None and not pd.isna(data['avg_round']) else 0
        
        self.stat_widgets['total_projects'].setText(str(total_projects))
        self.stat_widgets['projects_with_revision'].setText(str(projects_with_revision))
        self.stat_widgets['revision_rate'].setText(f"{revision_rate:.1f}%")
        self.stat_widgets['total_revisions'].setText(str(total_revisions))
        self.stat_widgets['avg_round'].setText(f"{avg_round:.1f}")
        self.stat_widgets['urgent_count'].setText(str(urgent_count))
    
    def load_projects_table(self, projects):
        self.table.setRowCount(len(projects))
        
        status_colors = {
            '待返稿': QColor(243, 156, 18),
            '已返稿': QColor(231, 76, 60),
            '已验收': QColor(46, 204, 113),
            '已完成': QColor(52, 152, 219),
        }
        
        for row, project in enumerate(projects):
            self.table.setItem(row, 0, QTableWidgetItem(str(project['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(project['project_no']))
            self.table.setItem(row, 2, QTableWidgetItem(project['project_name']))
            self.table.setItem(row, 3, QTableWidgetItem(project['client_name']))
            self.table.setItem(row, 4, QTableWidgetItem(project['draft_date'] or '-'))
            
            status_item = QTableWidgetItem(project['revision_status'])
            color = status_colors.get(project['revision_status'], QColor(100, 100, 100))
            status_item.setForeground(color)
            self.table.setItem(row, 5, status_item)
            
            self.table.setItem(row, 6, QTableWidgetItem(project['final_result'] or '-'))
            self.table.setItem(row, 7, QTableWidgetItem(str(project['revision_count'])))
    
    def get_selected_project_id(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            item = self.table.item(current_row, 0)
            if item:
                return int(item.text())
        return None
    
    def on_view_detail(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            self.show_warning("请先选择一个项目")
            return
        
        dialog = ProjectDetailDialog(self, project_id=project_id)
        if dialog.exec():
            self.load_data()
    
    def on_table_double_clicked(self, index):
        project_id = self.get_selected_project_id()
        if project_id:
            dialog = ProjectDetailDialog(self, project_id=project_id)
            if dialog.exec():
                self.load_data()
    
    def show_warning(self, message):
        InfoBar.warning(
            title="提示",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def refresh(self):
        current_index = self.actor_combo.currentIndex()
        self.load_actors()
        if current_index < self.actor_combo.count():
            self.actor_combo.setCurrentIndex(current_index)
        else:
            self.actor_combo.setCurrentIndex(0)
        self.load_data()

import pandas as pd
