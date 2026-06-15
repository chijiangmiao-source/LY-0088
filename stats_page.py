from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QFrame, QTableWidgetItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from qfluentwidgets import (CardWidget, TableWidget, ComboBox,
                            SubtitleLabel, TitleLabel)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams

import pandas as pd
import database

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsPage")
        
        self.setStyleSheet("""
            StatsPage { background-color: white; }
            QScrollArea { background-color: white; border: none; }
            QWidget#contentWidget { background-color: white; }
            QLabel { color: #333; }
        """)
        
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = TitleLabel("统计分析")
        layout.addWidget(title)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: white; }")
        
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_widget.setStyleSheet("#contentWidget { background-color: white; }")
        
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        summary_card = self.create_summary_card()
        content_layout.addWidget(summary_card)
        
        chart_row1 = QHBoxLayout()
        chart_row1.setSpacing(15)
        
        self.reason_chart_card, self.reason_figure, self.reason_canvas = self.create_chart_card("返稿原因分布")
        chart_row1.addWidget(self.reason_chart_card, 1)
        
        self.status_chart_card, self.status_figure, self.status_canvas = self.create_chart_card("项目状态分布")
        chart_row1.addWidget(self.status_chart_card, 1)
        
        content_layout.addLayout(chart_row1)
        
        self.monthly_chart_card, self.monthly_figure, self.monthly_canvas = self.create_wide_chart_card("月度项目与返稿趋势")
        content_layout.addWidget(self.monthly_chart_card)
        
        self.actor_card = self.create_actor_stat_card()
        content_layout.addWidget(self.actor_card)
        
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
    
    def create_summary_card(self):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QHBoxLayout(card)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        projects = database.get_all_projects()
        total_projects = len(projects)
        total_revisions = sum(p['revision_count'] for p in projects)
        projects_with_revision = sum(1 for p in projects if p['revision_count'] > 0)
        revision_rate = (projects_with_revision / total_projects * 100) if total_projects > 0 else 0
        
        avg_round = (total_revisions / projects_with_revision) if projects_with_revision > 0 else 0
        
        stats_data = [
            ("总项目数", total_projects, "#0078D4"),
            ("返稿项目数", projects_with_revision, "#E74C3C"),
            ("返稿率", f"{revision_rate:.1f}%", "#F39C12"),
            ("总返稿次数", total_revisions, "#9B59B6"),
            ("平均返稿轮次", f"{avg_round:.1f}", "#1ABC9C"),
        ]
        
        for label, value, color in stats_data:
            stat_widget = QWidget()
            stat_widget.setStyleSheet("background-color: transparent;")
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(5)
            stat_layout.setAlignment(Qt.AlignCenter)
            
            value_label = QLabel(str(value))
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color}; background-color: transparent;")
            
            label_label = QLabel(label)
            label_label.setAlignment(Qt.AlignCenter)
            label_label.setStyleSheet("font-size: 13px; color: #666; background-color: transparent;")
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(label_label)
            layout.addWidget(stat_widget)
        
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
    
    def create_actor_stat_card(self):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title_label = SubtitleLabel("配音员维度统计")
        layout.addWidget(title_label)
        
        self.actor_table = TableWidget()
        self.actor_table.setColumnCount(6)
        self.actor_table.setHorizontalHeaderLabels([
            "配音员", "总项目数", "返稿项目数", "总返稿次数", "平均返稿轮次", "加急次数"
        ])
        self.actor_table.verticalHeader().setVisible(False)
        self.actor_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.actor_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.actor_table)
        
        return card
    
    def load_statistics(self):
        self.plot_reason_chart()
        self.plot_status_chart()
        self.plot_monthly_chart()
        self.load_actor_stats()
    
    def plot_reason_chart(self):
        self.reason_figure.clear()
        ax = self.reason_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_revision_statistics()
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            colors = plt.cm.Set3(range(len(df)))
            wedges, texts, autotexts = ax.pie(
                df['count'], labels=df['reason'], autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.85
            )
            
            for text in texts:
                text.set_fontsize(9)
                text.set_color('#333')
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            ax.add_artist(centre_circle)
        
        self.reason_figure.tight_layout()
        self.reason_canvas.draw()
    
    def plot_status_chart(self):
        self.status_figure.clear()
        ax = self.status_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_status_statistics()
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            colors = ['#3498DB', '#E74C3C', '#2ECC71', '#F39C12']
            bars = ax.bar(df['revision_status'], df['count'], color=colors[:len(df)])
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom', fontsize=10, color='#333')
            
            ax.set_ylabel('项目数', color='#333')
            ax.tick_params(axis='x', rotation=15, colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='y', alpha=0.3, color='#ccc')
        
        self.status_figure.tight_layout()
        self.status_canvas.draw()
    
    def plot_monthly_chart(self):
        self.monthly_figure.clear()
        ax = self.monthly_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_monthly_statistics()
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            x = range(len(df['month']))
            width = 0.35
            
            bars1 = ax.bar([i - width/2 for i in x], df['total_projects'], width, 
                          label='项目数', color='#3498DB')
            bars2 = ax.bar([i + width/2 for i in x], df['total_revisions'], width,
                          label='返稿次数', color='#E74C3C')
            
            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9, color='#333')
            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9, color='#333')
            
            ax.set_xticks(x)
            ax.set_xticklabels(df['month'], rotation=30, ha='right', color='#333')
            ax.set_ylabel('数量', color='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.legend()
            ax.grid(axis='y', alpha=0.3, color='#ccc')
        
        self.monthly_figure.tight_layout()
        self.monthly_canvas.draw()
    
    def load_actor_stats(self):
        df = database.get_voice_actor_statistics()
        
        self.actor_table.setRowCount(len(df))
        
        for row, (_, data) in enumerate(df.iterrows()):
            self.actor_table.setItem(row, 0, QTableWidgetItem(str(data['voice_actor'])))
            self.actor_table.setItem(row, 1, QTableWidgetItem(str(int(data['total_projects']))))
            self.actor_table.setItem(row, 2, QTableWidgetItem(str(int(data['projects_with_revision']))))
            self.actor_table.setItem(row, 3, QTableWidgetItem(str(int(data['total_revisions']))))
            
            avg_round = data['avg_round'] if pd.notna(data['avg_round']) else 0
            self.actor_table.setItem(row, 4, QTableWidgetItem(f"{avg_round:.1f}"))
            
            urgent_count = data['urgent_count'] if pd.notna(data['urgent_count']) else 0
            self.actor_table.setItem(row, 5, QTableWidgetItem(str(int(urgent_count))))
    
    def refresh(self):
        self.load_statistics()
