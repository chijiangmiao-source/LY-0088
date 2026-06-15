from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                               QSpinBox, QCheckBox, QLabel)
from PySide6.QtCore import Qt, QDate
from qfluentwidgets import (LineEdit, ComboBox, DateEdit, TextEdit, 
                            PrimaryPushButton, PushButton, InfoBar, InfoBarPosition,
                            SpinBox, CheckBox)
import database

REVISION_REASONS = [
    '发音错误',
    '语调/语气问题',
    '语速问题',
    '情感表达不准确',
    '音质/录音问题',
    '断句/停顿问题',
    '内容修改',
    '客户要求调整',
    '其他'
]

class RevisionDialog(QDialog):
    def __init__(self, parent=None, project_id=None, revision_id=None):
        super().__init__(parent)
        self.project_id = project_id
        self.revision_id = revision_id
        self.setWindowTitle("编辑返稿记录" if revision_id else "新增返稿记录")
        self.resize(500, 500)
        
        self.init_ui()
        
        if revision_id:
            self.load_revision_data()
        else:
            self.set_default_round()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        self.revision_date_edit = DateEdit()
        self.revision_date_edit.setCalendarPopup(True)
        self.revision_date_edit.setDate(QDate.currentDate())
        form_layout.addRow("返稿日期:", self.revision_date_edit)
        
        self.reason_combo = ComboBox()
        self.reason_combo.addItems(REVISION_REASONS)
        self.reason_combo.setEditable(True)
        form_layout.addRow("返稿原因:", self.reason_combo)
        
        self.round_spin = SpinBox()
        self.round_spin.setMinimum(1)
        self.round_spin.setMaximum(99)
        form_layout.addRow("修改轮次:", self.round_spin)
        
        self.urgent_check = CheckBox("加急处理")
        form_layout.addRow("是否加急:", self.urgent_check)
        
        self.description_edit = TextEdit()
        self.description_edit.setPlaceholderText("请输入处理说明（可选）")
        self.description_edit.setFixedHeight(120)
        form_layout.addRow("处理说明:", self.description_edit)
        
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
    
    def set_default_round(self):
        if self.project_id:
            revisions = database.get_revisions_by_project(self.project_id)
            if revisions:
                max_round = max(r['round'] for r in revisions)
                self.round_spin.setValue(max_round + 1)
    
    def load_revision_data(self):
        revision = database.get_revision_by_id(self.revision_id)
        if revision:
            if revision['revision_date']:
                rev_date = QDate.fromString(revision['revision_date'], "yyyy-MM-dd")
                self.revision_date_edit.setDate(rev_date)
            
            if revision['reason'] in REVISION_REASONS:
                self.reason_combo.setCurrentText(revision['reason'])
            else:
                self.reason_combo.setCurrentText(revision['reason'])
            
            self.round_spin.setValue(revision['round'])
            self.urgent_check.setChecked(revision['is_urgent'] == 1)
            
            if revision['description']:
                self.description_edit.setPlainText(revision['description'])
    
    def on_ok_clicked(self):
        revision_date = self.revision_date_edit.date().toString("yyyy-MM-dd")
        reason = self.reason_combo.currentText().strip()
        round_num = self.round_spin.value()
        is_urgent = 1 if self.urgent_check.isChecked() else 0
        description = self.description_edit.toPlainText().strip()
        
        if not reason:
            self.show_error("请选择或输入返稿原因")
            return
        
        try:
            if self.revision_id:
                database.update_revision(
                    self.revision_id, revision_date, reason, round_num, is_urgent, description
                )
                self.show_success("返稿记录更新成功")
            else:
                database.add_revision(
                    self.project_id, revision_date, reason, round_num, is_urgent, description
                )
                self.show_success("返稿记录添加成功")
            
            self.accept()
        except Exception as e:
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
