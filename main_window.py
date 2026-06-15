from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon
from qfluentwidgets import (MSFluentWindow, NavigationItemPosition, TableWidget,
                            CardWidget, PrimaryPushButton, PushButton, ComboBox,
                            LineEdit, TitleLabel, InfoBar, InfoBarPosition,
                            TransparentToolButton, FluentIcon as FIF)
from project_dialog import ProjectDialog
from project_detail_dialog import ProjectDetailDialog
from stats_page import StatsPage
from voice_actor_page import VoiceActorPage
from archive_page import ArchivePage
from template_export_page import TemplateExportPage
import database

REVISION_STATUS = ['全部', '待返稿', '已返稿', '已验收', '已完成']

class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("配音返稿追踪器")
        self.resize(1200, 800)
        
        self.init_database()
        self.create_pages()
        self.init_navigation()
    
    def init_database(self):
        database.init_database()
    
    def create_pages(self):
        self.project_page = ProjectPage(self)
        self.stats_page = StatsPage(self)
        self.voice_actor_page = VoiceActorPage(self)
        self.archive_page = ArchivePage(self)
        self.template_export_page = TemplateExportPage(self)
        
        self.addSubInterface(self.project_page, FIF.HOME, "项目管理")
        self.addSubInterface(self.stats_page, FIF.BOOK_SHELF, "统计分析")
        self.addSubInterface(self.voice_actor_page, FIF.PEOPLE, "配音员维度")
        self.addSubInterface(self.archive_page, FIF.FOLDER, "交付归档")
        self.addSubInterface(self.template_export_page, FIF.SAVE_AS, "模板与导出")
        
        self.navigationInterface.setMinimumWidth(60)
    
    def init_navigation(self):
        self.stackedWidget.currentChanged.connect(self.on_page_changed)
    
    def on_page_changed(self, index):
        if index == 1:
            self.stats_page.refresh()
        elif index == 2:
            self.voice_actor_page.refresh()
        elif index == 3:
            self.archive_page.refresh()
        elif index == 4:
            self.template_export_page.refresh()
        elif index == 0:
            self.project_page.refresh()

class ProjectPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectPage")
        self.setStyleSheet("""
            ProjectPage { background-color: white; }
            QLabel { color: #333; }
        """)
        self.init_ui()
        self.load_filters()
        self.load_projects()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = TitleLabel("项目管理")
        layout.addWidget(title)
        
        filter_card = CardWidget()
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(15)
        
        search_label = QLabel("搜索：")
        filter_layout.addWidget(search_label)
        
        self.search_edit = LineEdit()
        self.search_edit.setPlaceholderText("搜索项目编号、名称、客户、配音员...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_edit, 1)
        
        status_label = QLabel("状态：")
        filter_layout.addWidget(status_label)
        
        self.status_combo = ComboBox()
        self.status_combo.addItems(REVISION_STATUS)
        self.status_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.status_combo)
        
        actor_label = QLabel("配音员：")
        filter_layout.addWidget(actor_label)
        
        self.actor_combo = ComboBox()
        self.actor_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.actor_combo)
        
        self.refresh_btn = TransparentToolButton(FIF.SYNC)
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(filter_card)
        
        btn_card = CardWidget()
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        btn_layout.setSpacing(10)
        
        self.add_btn = PrimaryPushButton("新增项目")
        self.add_btn.clicked.connect(self.on_add_project)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = PushButton("编辑项目")
        self.edit_btn.clicked.connect(self.on_edit_project)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = PushButton("删除项目")
        self.delete_btn.clicked.connect(self.on_delete_project)
        btn_layout.addWidget(self.delete_btn)
        
        self.detail_btn = PushButton("查看详情")
        self.detail_btn.clicked.connect(self.on_view_detail)
        btn_layout.addWidget(self.detail_btn)
        
        btn_layout.addStretch()
        
        self.stats_label = QLabel("共 0 条记录")
        self.stats_label.setStyleSheet("color: #666; font-size: 13px;")
        btn_layout.addWidget(self.stats_label)
        
        layout.addWidget(btn_card)
        
        self.table = TableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "项目编号", "项目名称", "客户名称", "配音员",
            "初稿日期", "预计交付", "风险等级", "返稿状态", "最终结果", "返稿次数"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setColumnHidden(0, True)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table, 1)
    
    def load_filters(self):
        actors = database.get_all_voice_actors()
        self.actor_combo.clear()
        self.actor_combo.addItem("全部")
        for actor in actors:
            self.actor_combo.addItem(actor)
    
    def load_projects(self):
        search_keyword = self.search_edit.text().strip()
        status_filter = self.status_combo.currentText()
        actor_filter = self.actor_combo.currentText()
        
        projects = database.get_projects_with_risk(
            search_keyword=search_keyword if search_keyword else None,
            status_filter=status_filter,
            actor_filter=actor_filter
        )
        
        self.table.setRowCount(len(projects))
        self.stats_label.setText(f"共 {len(projects)} 条记录")
        
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
            self.table.setItem(row, 4, QTableWidgetItem(project['voice_actor']))
            self.table.setItem(row, 5, QTableWidgetItem(project['draft_date'] or '-'))
            self.table.setItem(row, 6, QTableWidgetItem(project['expected_delivery_date'] or '-'))
            
            risk_level = project.get('risk_level', '低风险')
            risk_color = QColor(project.get('risk_color', '#2ECC71'))
            risk_item = QTableWidgetItem(risk_level)
            risk_item.setForeground(risk_color)
            risk_font = risk_item.font()
            risk_font.setBold(True)
            risk_item.setFont(risk_font)
            risk_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 7, risk_item)
            
            status_item = QTableWidgetItem(project['revision_status'])
            color = status_colors.get(project['revision_status'], QColor(100, 100, 100))
            status_item.setForeground(color)
            status_item.setFont(self.table.font())
            self.table.setItem(row, 8, status_item)
            
            self.table.setItem(row, 9, QTableWidgetItem(project['final_result'] or '-'))
            
            revision_count = project['revision_count']
            count_item = QTableWidgetItem(str(revision_count))
            if revision_count > 0:
                count_item.setForeground(QColor(231, 76, 60))
            self.table.setItem(row, 10, count_item)
            
            if risk_level == '高风险':
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 240, 240))
            elif risk_level == '中风险':
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 250, 235))
    
    def get_selected_project_id(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            item = self.table.item(current_row, 0)
            if item:
                return int(item.text())
        return None
    
    def on_search_changed(self):
        self.load_projects()
    
    def on_filter_changed(self):
        self.load_projects()
    
    def on_add_project(self):
        dialog = ProjectDialog(self)
        if dialog.exec():
            self.load_filters()
            self.load_projects()
    
    def on_edit_project(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            self.show_warning("请先选择一个项目")
            return
        
        dialog = ProjectDialog(self, project_id=project_id)
        if dialog.exec():
            self.load_filters()
            self.load_projects()
    
    def on_delete_project(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            self.show_warning("请先选择一个项目")
            return
        
        project = database.get_project_by_id(project_id)
        project_name = project['project_name'] if project else '该项目'
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除项目「{project_name}」吗？\n所有相关的返稿记录也将被删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            database.delete_project(project_id)
            self.load_filters()
            self.load_projects()
            self.show_success("删除成功")
    
    def on_view_detail(self):
        project_id = self.get_selected_project_id()
        if not project_id:
            self.show_warning("请先选择一个项目")
            return
        
        dialog = ProjectDetailDialog(self, project_id=project_id)
        if dialog.exec():
            self.load_filters()
            self.load_projects()
    
    def on_table_double_clicked(self, index):
        project_id = self.get_selected_project_id()
        if project_id:
            dialog = ProjectDetailDialog(self, project_id=project_id)
            if dialog.exec():
                self.load_filters()
                self.load_projects()
    
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
    
    def refresh(self):
        self.load_filters()
        self.load_projects()
