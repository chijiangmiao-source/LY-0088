from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QFrame, QTableWidgetItem)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPalette, QColor
from qfluentwidgets import (CardWidget, TableWidget, ComboBox,
                            SubtitleLabel, TitleLabel, DateEdit)

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
        self.load_filters()
        self.load_statistics()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = TitleLabel("返稿预警与复盘看板")
        layout.addWidget(title)
        
        filter_card = CardWidget()
        filter_card.setStyleSheet("CardWidget { background-color: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; }")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 12, 15, 12)
        filter_layout.setSpacing(15)
        
        filter_title = QLabel("筛选条件：")
        filter_title.setStyleSheet("font-weight: bold; color: #333; background-color: transparent;")
        filter_layout.addWidget(filter_title)
        
        date_start_label = QLabel("开始日期：")
        date_start_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(date_start_label)
        
        self.date_start = DateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
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
        self.client_combo.setMinimumWidth(150)
        self.client_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.client_combo)
        
        actor_label = QLabel("配音员：")
        actor_label.setStyleSheet("background-color: transparent;")
        filter_layout.addWidget(actor_label)
        
        self.actor_combo = ComboBox()
        self.actor_combo.setMinimumWidth(150)
        self.actor_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.actor_combo)
        
        filter_layout.addStretch()
        
        layout.addWidget(filter_card)
        
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
        
        risk_overview_card, self.risk_figure, self.risk_canvas = self.create_chart_card("风险等级分布")
        content_layout.addWidget(risk_overview_card)
        
        chart_row1 = QHBoxLayout()
        chart_row1.setSpacing(15)
        
        self.overdue_chart_card, self.overdue_figure, self.overdue_canvas = self.create_chart_card("超期项目占比")
        chart_row1.addWidget(self.overdue_chart_card, 1)
        
        self.reason_chart_card, self.reason_figure, self.reason_canvas = self.create_chart_card("高频返稿原因")
        chart_row1.addWidget(self.reason_chart_card, 1)
        
        content_layout.addLayout(chart_row1)
        
        self.cost_chart_card, self.cost_figure, self.cost_canvas = self.create_wide_chart_card("客户维度返工成本分布")
        content_layout.addWidget(self.cost_chart_card)
        
        self.monthly_chart_card, self.monthly_figure, self.monthly_canvas = self.create_wide_chart_card("月度项目与返稿趋势")
        content_layout.addWidget(self.monthly_chart_card)
        
        self.actor_card = self.create_actor_stat_card()
        content_layout.addWidget(self.actor_card)
        
        self.client_detail_card = self.create_client_detail_card()
        content_layout.addWidget(self.client_detail_card)
        
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
            ("total_projects", "总项目数", "#0078D4"),
            ("overdue_count", "超期项目数", "#E74C3C"),
            ("overdue_rate", "超期率", "#E67E22"),
            ("high_risk_count", "高风险项目", "#C0392B"),
            ("projects_with_revision", "返稿项目数", "#9B59B6"),
            ("avg_round", "平均返稿轮次", "#1ABC9C"),
            ("urgent_count", "加急返稿数", "#E67E22"),
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
    
    def create_client_detail_card(self):
        card = CardWidget()
        card.setStyleSheet("CardWidget { background-color: white; border: 1px solid #e8e8e8; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title_label = SubtitleLabel("客户返工成本明细")
        layout.addWidget(title_label)
        
        self.client_table = TableWidget()
        self.client_table.setColumnCount(7)
        self.client_table.setHorizontalHeaderLabels([
            "客户名称", "总项目数", "返稿项目数", "总返稿次数", "平均返稿轮次", "加急次数", "返工成本指数"
        ])
        self.client_table.verticalHeader().setVisible(False)
        self.client_table.setEditTriggers(TableWidget.NoEditTriggers)
        self.client_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.client_table)
        
        return card
    
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
        self.load_statistics()
    
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
    
    def load_statistics(self):
        params = self.get_filter_params()
        
        self.load_summary(params)
        self.plot_risk_chart(params)
        self.plot_overdue_chart(params)
        self.plot_reason_chart(params)
        self.plot_cost_chart(params)
        self.plot_monthly_chart(params)
        self.load_actor_stats(params)
        self.load_client_detail(params)
    
    def load_summary(self, params):
        projects = database.get_projects_with_risk(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        overdue_df = database.get_overdue_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        total_projects = len(projects)
        projects_with_revision = sum(1 for p in projects if p['revision_count'] > 0)
        total_revisions = sum(p['revision_count'] for p in projects)
        high_risk_count = sum(1 for p in projects if p['risk_level'] == '高风险')
        urgent_count = sum(1 for p in projects if p.get('has_urgent', 0) == 1)
        
        avg_round = (total_revisions / projects_with_revision) if projects_with_revision > 0 else 0
        
        overdue_count = int(overdue_df.iloc[0]['overdue_count']) if not overdue_df.empty else 0
        overdue_rate = (overdue_count / total_projects * 100) if total_projects > 0 else 0
        
        self.summary_widgets['total_projects'].setText(str(total_projects))
        self.summary_widgets['overdue_count'].setText(str(overdue_count))
        self.summary_widgets['overdue_rate'].setText(f"{overdue_rate:.1f}%")
        self.summary_widgets['high_risk_count'].setText(str(high_risk_count))
        self.summary_widgets['projects_with_revision'].setText(str(projects_with_revision))
        self.summary_widgets['avg_round'].setText(f"{avg_round:.1f}")
        self.summary_widgets['urgent_count'].setText(str(urgent_count))
    
    def plot_risk_chart(self, params):
        self.risk_figure.clear()
        ax = self.risk_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_risk_level_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        if df.empty or df['count'].sum() == 0:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            colors = ['#E74C3C', '#F39C12', '#2ECC71']
            risk_order = ['高风险', '中风险', '低风险']
            df_sorted = df.set_index('risk_level').reindex(risk_order).reset_index()
            df_sorted = df_sorted.fillna(0)
            
            wedges, texts, autotexts = ax.pie(
                df_sorted['count'], labels=df_sorted['risk_level'], autopct='%1.1f%%',
                colors=colors, startangle=90, pctdistance=0.80
            )
            
            for text in texts:
                text.set_fontsize(10)
                text.set_color('#333')
            for autotext in autotexts:
                autotext.set_fontsize(9)
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            centre_circle = plt.Circle((0, 0), 0.60, fc='white')
            ax.add_artist(centre_circle)
            
            total = int(df_sorted['count'].sum())
            ax.text(0, 0.05, f'总计\n{total}', ha='center', va='center', 
                    fontsize=12, color='#333', fontweight='bold')
        
        self.risk_figure.tight_layout()
        self.risk_canvas.draw()
    
    def plot_overdue_chart(self, params):
        self.overdue_figure.clear()
        ax = self.overdue_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_overdue_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            data = df.iloc[0]
            overdue_count = int(data['overdue_count'])
            on_time_count = int(data['on_time_count'])
            completed_count = int(data['completed_count'])
            
            categories = ['超期未完成', '按期进行中', '已完成/验收']
            values = [overdue_count, on_time_count, completed_count]
            colors = ['#E74C3C', '#3498DB', '#2ECC71']
            
            total = sum(values)
            if total == 0:
                ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                        fontsize=14, color='gray', transform=ax.transAxes)
                ax.set_axis_off()
            else:
                wedges, texts, autotexts = ax.pie(
                    values, labels=categories, autopct='%1.1f%%',
                    colors=colors, startangle=90, pctdistance=0.80
                )
                
                for text in texts:
                    text.set_fontsize(9)
                    text.set_color('#333')
                for autotext in autotexts:
                    autotext.set_fontsize(8)
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                
                centre_circle = plt.Circle((0, 0), 0.60, fc='white')
                ax.add_artist(centre_circle)
                
                ax.text(0, 0.05, f'超期率\n{(overdue_count/total*100):.1f}%', 
                        ha='center', va='center', fontsize=11, color='#E74C3C', fontweight='bold')
        
        self.overdue_figure.tight_layout()
        self.overdue_canvas.draw()
    
    def plot_reason_chart(self, params):
        self.reason_figure.clear()
        ax = self.reason_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_revision_reasons_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            df_top = df.head(8)
            
            colors = plt.cm.Set3(range(len(df_top)))
            bars = ax.barh(df_top['reason'][::-1], df_top['count'][::-1], color=colors)
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{int(width)}', ha='left', va='center', fontsize=9, color='#333')
            
            ax.set_xlabel('返稿次数', color='#333')
            ax.tick_params(axis='x', colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')
        
        self.reason_figure.tight_layout()
        self.reason_canvas.draw()
    
    def plot_cost_chart(self, params):
        self.cost_figure.clear()
        ax = self.cost_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_client_rework_cost_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        if df.empty or df['rework_cost_score'].sum() == 0:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            df_top = df.head(10)
            
            norm = plt.Normalize(df_top['rework_cost_score'].min(), df_top['rework_cost_score'].max())
            colors = plt.cm.Reds(norm(df_top['rework_cost_score']))
            
            bars = ax.barh(df_top['client_name'][::-1], df_top['rework_cost_score'][::-1], 
                          color=colors[::-1])
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f' {width:.0f}', ha='left', va='center', fontsize=9, color='#333')
            
            ax.set_xlabel('返工成本指数', color='#333')
            ax.set_title('返工成本指数 = 返稿次数×10 + 加急次数×5 + 最高轮次×8', 
                        fontsize=10, color='#666', pad=10)
            ax.tick_params(axis='x', colors='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, color='#ccc')
        
        self.cost_figure.tight_layout()
        self.cost_canvas.draw()
    
    def plot_monthly_chart(self, params):
        self.monthly_figure.clear()
        ax = self.monthly_figure.add_subplot(111)
        ax.set_facecolor('white')
        
        df = database.get_monthly_trend_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        if df.empty:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', 
                    fontsize=14, color='gray', transform=ax.transAxes)
            ax.set_axis_off()
        else:
            x = range(len(df['month']))
            width = 0.25
            
            bars1 = ax.bar([i - width for i in x], df['total_projects'], width, 
                          label='项目数', color='#3498DB')
            bars2 = ax.bar(x, df['total_revisions'], width,
                          label='返稿次数', color='#E74C3C')
            bars3 = ax.bar([i + width for i in x], df['urgent_count'], width,
                          label='加急次数', color='#F39C12')
            
            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom', fontsize=8, color='#333')
            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom', fontsize=8, color='#333')
            for bar in bars3:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom', fontsize=8, color='#333')
            
            ax.set_xticks(x)
            ax.set_xticklabels(df['month'], rotation=30, ha='right', color='#333')
            ax.set_ylabel('数量', color='#333')
            ax.tick_params(axis='y', colors='#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.legend(fontsize=9)
            ax.grid(axis='y', alpha=0.3, color='#ccc')
        
        self.monthly_figure.tight_layout()
        self.monthly_canvas.draw()
    
    def load_actor_stats(self, params):
        df = database.get_voice_actor_statistics()
        
        if params['actor_filter'] and params['actor_filter'] != '全部':
            df = df[df['voice_actor'] == params['actor_filter']]
        
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
    
    def load_client_detail(self, params):
        df = database.get_client_rework_cost_statistics(
            start_date=params['start_date'],
            end_date=params['end_date'],
            client_filter=params['client_filter'],
            actor_filter=params['actor_filter']
        )
        
        self.client_table.setRowCount(len(df))
        
        for row, (_, data) in enumerate(df.iterrows()):
            self.client_table.setItem(row, 0, QTableWidgetItem(str(data['client_name'])))
            self.client_table.setItem(row, 1, QTableWidgetItem(str(int(data['total_projects']))))
            self.client_table.setItem(row, 2, QTableWidgetItem(str(int(data['projects_with_revision']))))
            self.client_table.setItem(row, 3, QTableWidgetItem(str(int(data['total_revisions']))))
            
            avg_round = data['avg_round'] if pd.notna(data['avg_round']) else 0
            self.client_table.setItem(row, 4, QTableWidgetItem(f"{avg_round:.1f}"))
            
            urgent_count = data['urgent_count'] if pd.notna(data['urgent_count']) else 0
            self.client_table.setItem(row, 5, QTableWidgetItem(str(int(urgent_count))))
            
            cost_score = data['rework_cost_score'] if pd.notna(data['rework_cost_score']) else 0
            cost_item = QTableWidgetItem(f"{cost_score:.0f}")
            if cost_score > 50:
                cost_item.setForeground(QColor('#E74C3C'))
                cost_font = cost_item.font()
                cost_font.setBold(True)
                cost_item.setFont(cost_font)
            self.client_table.setItem(row, 6, cost_item)
    
    def refresh(self):
        self.load_filters()
        self.load_statistics()
