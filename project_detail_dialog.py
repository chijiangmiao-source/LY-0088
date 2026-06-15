from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from qfluentwidgets import (TableWidget, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, CardWidget, SubtitleLabel)
from revision_dialog import RevisionDialog
import database

class ProjectDetailDialog(QDialog):
    def __init__(self, parent=None, project_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("项目详情")
        self.resize(1000, 650)
        
        self.setStyleSheet("""
            ProjectDetailDialog { background-color: white; }
            QLabel { color: #333; }
        """)
        
        self.init_ui()
        self.load_project_info()
        self.load_revision_list()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_card = CardWidget(self)
        info_card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(20, 15, 20, 15)
        
        self.project_info_label = QLabel()
        self.project_info_label.setStyleSheet("font-size: 14px; line-height: 2; color: #333; background-color: transparent;")
        info_layout.addWidget(self.project_info_label)
        
        layout.addWidget(info_card)
        
        self.risk_card = CardWidget(self)
        self.risk_layout = QVBoxLayout(self.risk_card)
        self.risk_layout.setSpacing(10)
        self.risk_layout.setContentsMargins(20, 15, 20, 15)
        
        self.risk_title_label = QLabel()
        self.risk_title_label.setStyleSheet("font-size: 16px; font-weight: bold; background-color: transparent;")
        self.risk_layout.addWidget(self.risk_title_label)
        
        self.risk_factors_label = QLabel()
        self.risk_factors_label.setStyleSheet("font-size: 13px; line-height: 1.8; color: #555; background-color: transparent;")
        self.risk_layout.addWidget(self.risk_factors_label)
        
        layout.addWidget(self.risk_card)
        
        section_label = SubtitleLabel("返稿记录")
        section_label.setStyleSheet("background-color: transparent;")
        layout.addWidget(section_label)
        
        btn_layout = QHBoxLayout()
        self.add_revision_btn = PrimaryPushButton("新增返稿记录")
        self.add_revision_btn.clicked.connect(self.on_add_revision)
        btn_layout.addWidget(self.add_revision_btn)
        
        self.edit_revision_btn = PushButton("编辑选中")
        self.edit_revision_btn.clicked.connect(self.on_edit_revision)
        btn_layout.addWidget(self.edit_revision_btn)
        
        self.delete_revision_btn = PushButton("删除选中")
        self.delete_revision_btn.clicked.connect(self.on_delete_revision)
        btn_layout.addWidget(self.delete_revision_btn)
        
        btn_layout.addStretch()
        
        self.record_count_label = QLabel("共 0 条记录")
        self.record_count_label.setStyleSheet("color: #666; font-size: 13px; background-color: transparent;")
        btn_layout.addWidget(self.record_count_label)
        
        layout.addLayout(btn_layout)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "返稿日期", "返稿原因", "修改轮次", "是否加急", "处理说明"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setColumnHidden(0, True)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        self.table.setStyleSheet("""
            QTableWidget { 
                background-color: white; 
                gridline-color: #e8e8e8;
                alternate-background-color: #fafafa;
            }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section { 
                background-color: #f5f5f5; 
                padding: 8px; 
                border: none; 
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
            }
        """)
        
        layout.addWidget(self.table, 1)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.close_btn = PushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
    
    def load_project_info(self):
        project = database.get_project_by_id(self.project_id)
        if project:
            revisions = database.get_revisions_by_project(self.project_id)
            project['revision_count'] = len(revisions)
            project['max_round'] = max((r['round'] for r in revisions), default=0)
            project['has_urgent'] = 1 if any(r['is_urgent'] for r in revisions) else 0
            
            status_colors = {
                '待返稿': '#F39C12',
                '已返稿': '#E74C3C',
                '已验收': '#2ECC71',
                '已完成': '#3498DB',
            }
            status_color = status_colors.get(project['revision_status'], '#666')
            
            info_text = f"""
            <div style='font-weight: bold; font-size: 18px; margin-bottom: 12px; color: #222;'>
                {project['project_name']} 
                <span style='color: #888; font-weight: normal; font-size: 14px;'>({project['project_no']})</span>
            </div>
            <div style='font-size: 14px;'>
                <b>客户名称：</b>{project['client_name']}&nbsp;&nbsp;&nbsp;&nbsp;
                <b>配音员：</b>{project['voice_actor']}&nbsp;&nbsp;&nbsp;&nbsp;
                <b>返稿状态：</b><span style='color: {status_color}; font-weight: bold;'>{project['revision_status']}</span>
            </div>
            <div style='font-size: 14px;'>
                <b>初稿日期：</b>{project['draft_date'] or '-'}&nbsp;&nbsp;&nbsp;&nbsp;
                <b>预计交付日期：</b>{project['expected_delivery_date'] or '-'}&nbsp;&nbsp;&nbsp;&nbsp;
                <b>最终结果：</b>{project['final_result'] or '-'}
            </div>
            """
            self.project_info_label.setText(info_text)
            
            self.load_risk_info(project)
    
    def load_risk_info(self, project):
        risk_info = database.calculate_project_risk(project)
        
        risk_level = risk_info['risk_level']
        risk_color = risk_info['risk_color']
        risk_factors = risk_info['risk_factors']
        risk_score = risk_info['risk_score']
        
        if risk_level == '高风险':
            bg_color = '#FFF0F0'
            border_color = '#E74C3C'
        elif risk_level == '中风险':
            bg_color = '#FFFAEB'
            border_color = '#F39C12'
        else:
            bg_color = '#EAFBF1'
            border_color = '#2ECC71'
        
        self.risk_card.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {bg_color}; 
                border: 2px solid {border_color}; 
                border-radius: 8px; 
            }}
        """)
        
        title_text = f"""
        <span style='color: {risk_color};'>⚠ 风险等级：{risk_level}</span>
        <span style='color: #888; font-size: 13px; font-weight: normal;'>&nbsp;&nbsp;(风险评分: {risk_score})</span>
        """
        self.risk_title_label.setText(title_text)
        
        if risk_factors:
            factors_html = '<b>风险因素：</b><br>'
            for factor in risk_factors:
                factors_html += f'&nbsp;&nbsp;• {factor}<br>'
        else:
            factors_html = '<b>风险因素：</b>暂无明显风险因素'
        
        self.risk_factors_label.setText(factors_html)
    
    def load_revision_list(self):
        revisions = database.get_revisions_by_project(self.project_id)
        self.table.setRowCount(len(revisions))
        self.record_count_label.setText(f"共 {len(revisions)} 条记录")
        
        urgent_color = QColor(231, 76, 60)
        
        for row, rev in enumerate(revisions):
            self.table.setItem(row, 0, QTableWidgetItem(str(rev['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(rev['revision_date']))
            self.table.setItem(row, 2, QTableWidgetItem(rev['reason']))
            self.table.setItem(row, 3, QTableWidgetItem(f"第 {rev['round']} 轮"))
            
            urgent_item = QTableWidgetItem("是" if rev['is_urgent'] else "否")
            if rev['is_urgent']:
                urgent_item.setForeground(urgent_color)
                urgent_font = urgent_item.font()
                urgent_font.setBold(True)
                urgent_item.setFont(urgent_font)
            self.table.setItem(row, 4, urgent_item)
            
            desc = rev['description'] or '-'
            if len(desc) > 80:
                desc = desc[:80] + '...'
            self.table.setItem(row, 5, QTableWidgetItem(desc))
    
    def get_selected_revision_id(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            item = self.table.item(current_row, 0)
            if item:
                return int(item.text())
        return None
    
    def on_table_double_clicked(self, index):
        revision_id = self.get_selected_revision_id()
        if revision_id:
            self.on_edit_revision()
    
    def on_add_revision(self):
        dialog = RevisionDialog(self, project_id=self.project_id)
        if dialog.exec():
            self.load_revision_list()
            self.load_project_info()
            self.show_success("返稿记录添加成功")
    
    def on_edit_revision(self):
        revision_id = self.get_selected_revision_id()
        if not revision_id:
            self.show_warning("请先选择一条返稿记录")
            return
        
        dialog = RevisionDialog(self, revision_id=revision_id)
        if dialog.exec():
            self.load_revision_list()
            self.show_success("返稿记录更新成功")
    
    def on_delete_revision(self):
        revision_id = self.get_selected_revision_id()
        if not revision_id:
            self.show_warning("请先选择一条返稿记录")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这条返稿记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            database.delete_revision(revision_id)
            self.load_revision_list()
            self.load_project_info()
            self.show_success("删除成功")
    
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
    
    def show_success(self, message):
        InfoBar.success(
            title="成功",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
