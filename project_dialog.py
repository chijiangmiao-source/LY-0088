from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QLineEdit, QComboBox, QDateEdit, QTextEdit, 
                               QDialogButtonBox, QLabel, QMessageBox)
from PySide6.QtCore import Qt, QDate
from qfluentwidgets import (LineEdit, ComboBox, DateEdit, TextEdit, 
                            PrimaryPushButton, PushButton, InfoBar, InfoBarPosition)
from datetime import datetime
import database

REVISION_STATUS = ['待返稿', '已返稿', '已验收', '已完成']
FINAL_RESULTS = ['', '通过', '部分通过', '未通过', '其他']

class ProjectDialog(QDialog):
    def __init__(self, parent=None, project_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle("编辑项目" if project_id else "新增项目")
        self.resize(500, 600)
        
        self.init_ui()
        
        if project_id:
            self.load_project_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        self.project_no_edit = LineEdit()
        self.project_no_edit.setPlaceholderText("请输入项目编号")
        form_layout.addRow("项目编号:", self.project_no_edit)
        
        self.project_name_edit = LineEdit()
        self.project_name_edit.setPlaceholderText("请输入项目名称")
        form_layout.addRow("项目名称:", self.project_name_edit)
        
        self.client_name_edit = LineEdit()
        self.client_name_edit.setPlaceholderText("请输入客户名称")
        form_layout.addRow("客户名称:", self.client_name_edit)
        
        self.voice_actor_edit = LineEdit()
        self.voice_actor_edit.setPlaceholderText("请输入配音员")
        form_layout.addRow("配音员:", self.voice_actor_edit)
        
        self.draft_date_edit = DateEdit()
        self.draft_date_edit.setCalendarPopup(True)
        self.draft_date_edit.setDate(QDate.currentDate())
        self.draft_date_edit.dateChanged.connect(self.on_draft_date_changed)
        form_layout.addRow("初稿日期:", self.draft_date_edit)
        
        self.expected_date_edit = DateEdit()
        self.expected_date_edit.setCalendarPopup(True)
        self.expected_date_edit.setDate(QDate.currentDate().addDays(7))
        self.expected_date_edit.setMinimumDate(QDate.currentDate())
        self.expected_date_edit.setSpecialValueText(" ")
        form_layout.addRow("预计交付日期:", self.expected_date_edit)
        
        self.status_combo = ComboBox()
        self.status_combo.addItems(REVISION_STATUS)
        form_layout.addRow("返稿状态:", self.status_combo)
        
        self.final_result_combo = ComboBox()
        self.final_result_combo.addItems(FINAL_RESULTS)
        form_layout.addRow("最终结果:", self.final_result_combo)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = PrimaryPushButton("确定")
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def load_project_data(self):
        project = database.get_project_by_id(self.project_id)
        if project:
            self.project_no_edit.setText(project['project_no'])
            self.project_name_edit.setText(project['project_name'])
            self.client_name_edit.setText(project['client_name'])
            self.voice_actor_edit.setText(project['voice_actor'])
            
            draft_date = None
            if project['draft_date']:
                draft_date = QDate.fromString(project['draft_date'], "yyyy-MM-dd")
                self.draft_date_edit.setDate(draft_date)
                self.expected_date_edit.setMinimumDate(draft_date)
            
            if project['expected_delivery_date']:
                exp_date = QDate.fromString(project['expected_delivery_date'], "yyyy-MM-dd")
                if draft_date and exp_date < draft_date:
                    exp_date = draft_date
                self.expected_date_edit.setDate(exp_date)
            
            if project['revision_status'] in REVISION_STATUS:
                self.status_combo.setCurrentText(project['revision_status'])
            
            if project['final_result'] in FINAL_RESULTS:
                self.final_result_combo.setCurrentText(project['final_result'])
    
    def on_draft_date_changed(self, new_date):
        self.expected_date_edit.setMinimumDate(new_date)
        if self.expected_date_edit.date() < new_date:
            self.expected_date_edit.setDate(new_date)
    
    def on_ok_clicked(self):
        project_no = self.project_no_edit.text().strip()
        project_name = self.project_name_edit.text().strip()
        client_name = self.client_name_edit.text().strip()
        voice_actor = self.voice_actor_edit.text().strip()
        draft_date = self.draft_date_edit.date().toString("yyyy-MM-dd")
        expected_date = self.expected_date_edit.date().toString("yyyy-MM-dd")
        status = self.status_combo.currentText()
        final_result = self.final_result_combo.currentText()
        
        if not project_no:
            self.show_error("请输入项目编号")
            return
        
        if not project_name:
            self.show_error("请输入项目名称")
            return
        
        if not client_name:
            self.show_error("请输入客户名称")
            return
        
        if not voice_actor:
            self.show_error("请输入配音员")
            return
        
        if self.expected_date_edit.date() < self.draft_date_edit.date():
            self.show_error("预计交付日期不能早于初稿日期")
            return
        
        try:
            if self.project_id:
                database.update_project(
                    self.project_id, project_no, project_name, client_name,
                    voice_actor, draft_date, expected_date, status, final_result
                )
                self.show_success("项目更新成功")
            else:
                database.add_project(
                    project_no, project_name, client_name, voice_actor,
                    draft_date, expected_date, status, final_result
                )
                self.show_success("项目添加成功")
            
            self.accept()
        except ValueError as e:
            self.show_error(str(e))
    
    def show_error(self, message):
        InfoBar.error(
            title="错误",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
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
