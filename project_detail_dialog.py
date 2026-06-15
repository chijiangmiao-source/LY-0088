from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QMessageBox)
from PySide6.QtCore import Qt
from qfluentwidgets import (TableWidget, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, CardWidget)
from revision_dialog import RevisionDialog
import database

class ProjectDetailDialog(QDialog):
    def __init__(self, parent=None, project_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("项目详情")
        self.resize(900, 600)
        
        self.init_ui()
        self.load_project_info()
        self.load_revision_list()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_card = CardWidget(self)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        self.project_info_label = QLabel()
        self.project_info_label.setStyleSheet("font-size: 14px; line-height: 1.8;")
        info_layout.addWidget(self.project_info_label)
        
        layout.addWidget(info_card)
        
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
        
        self.close_btn = PushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
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
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)
        
        layout.addWidget(self.table, 1)
    
    def load_project_info(self):
        project = database.get_project_by_id(self.project_id)
        if project:
            info_text = f"""
            <div style='font-weight: bold; font-size: 16px; margin-bottom: 10px;'>
                {project['project_name']} ({project['project_no']})
            </div>
            <div>
                <b>客户名称：</b>{project['client_name']}&nbsp;&nbsp;&nbsp;
                <b>配音员：</b>{project['voice_actor']}&nbsp;&nbsp;&nbsp;
                <b>返稿状态：</b>{project['revision_status']}
            </div>
            <div>
                <b>初稿日期：</b>{project['draft_date'] or '-'}&nbsp;&nbsp;&nbsp;
                <b>预计交付日期：</b>{project['expected_delivery_date'] or '-'}&nbsp;&nbsp;&nbsp;
                <b>最终结果：</b>{project['final_result'] or '-'}
            </div>
            """
            self.project_info_label.setText(info_text)
    
    def load_revision_list(self):
        revisions = database.get_revisions_by_project(self.project_id)
        self.table.setRowCount(len(revisions))
        
        for row, rev in enumerate(revisions):
            self.table.setItem(row, 0, QTableWidgetItem(str(rev['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(rev['revision_date']))
            self.table.setItem(row, 2, QTableWidgetItem(rev['reason']))
            self.table.setItem(row, 3, QTableWidgetItem(f"第 {rev['round']} 轮"))
            self.table.setItem(row, 4, QTableWidgetItem("是" if rev['is_urgent'] else "否"))
            
            desc = rev['description'] or '-'
            if len(desc) > 50:
                desc = desc[:50] + '...'
            self.table.setItem(row, 5, QTableWidgetItem(desc))
    
    def get_selected_revision_id(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            item = self.table.item(current_row, 0)
            if item:
                return int(item.text())
        return None
    
    def on_add_revision(self):
        dialog = RevisionDialog(self, project_id=self.project_id)
        if dialog.exec():
            self.load_revision_list()
            self.load_project_info()
    
    def on_edit_revision(self):
        revision_id = self.get_selected_revision_id()
        if not revision_id:
            self.show_warning("请先选择一条返稿记录")
            return
        
        dialog = RevisionDialog(self, revision_id=revision_id)
        if dialog.exec():
            self.load_revision_list()
    
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
