import sys
import numpy as np
import random
import google.generativeai as genai  # Gemini API Integration
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QWidget, QMessageBox, QTabWidget, QTextEdit,
    QGroupBox, QInputDialog, QFrame, QSplitter, QComboBox, QStyleFactory,
    QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

genai.configure(api_key="AIzaSyD3LIZdg1iL04_UyEvVCVBoDdeHDszD6Xs")  # Replace with your actual API key

# Theme colors
class Themes:
    LIGHT = {
        "window": "#f0f0f0",
        "text": "#333333",
        "button": "#4a86e8",
        "button_text": "#ffffff",
        "card": "#ffffff",
        "card_border": "#dddddd",
        "input_bg": "#ffffff",
        "input_border": "#cccccc",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "accent": "#4a86e8",
        "gantt_bg": "#ffffff",
        "table_header": "#e9ecef",
        "table_row_alt": "#f8f9fa"
    }
    
    DARK = {
        "window": "#2d2d2d",
        "text": "#e0e0e0",
        "button": "#3366cc",
        "button_text": "#ffffff",
        "card": "#3d3d3d",
        "card_border": "#555555",
        "input_bg": "#444444",
        "input_border": "#666666",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "accent": "#4a86e8",
        "gantt_bg": "#3d3d3d",
        "table_header": "#444444",
        "table_row_alt": "#383838"
    }

class Task:
    def __init__(self, id, arrival_time, execution_time, priority, energy_intensity, cpu_demand):
        self.id = id
        self.arrival_time = arrival_time
        self.execution_time = execution_time
        self.priority = priority
        self.energy_intensity = energy_intensity
        self.cpu_demand = cpu_demand
        # For scheduling results
        self.completion_time = 0
        self.turnaround_time = 0
        self.waiting_time = 0

class StyledButton(QPushButton):
    def __init__(self, text, icon=None, is_primary=True, parent=None):
        super().__init__(text, parent)
        self.is_primary = is_primary
        if icon:
            self.setIcon(icon)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        
    def update_style(self, theme):
        if self.is_primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['button']};
                    color: {theme['button_text']};
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(theme['button'])};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(theme['button'])};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {theme['text']};
                    border: 1px solid {theme['button']};
                    border-radius: 4px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {theme['button']};
                    color: {theme['button_text']};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(theme['button'])};
                }}
            """)
    
    def lighten_color(self, hex_color, amount=20):
        # Simple lightening function
        r = min(255, int(hex_color[1:3], 16) + amount)
        g = min(255, int(hex_color[3:5], 16) + amount)
        b = min(255, int(hex_color[5:7], 16) + amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def darken_color(self, hex_color, amount=20):
        # Simple darkening function
        r = max(0, int(hex_color[1:3], 16) - amount)
        g = max(0, int(hex_color[3:5], 16) - amount)
        b = max(0, int(hex_color[5:7], 16) - amount)
        return f"#{r:02x}{g:02x}{b:02x}"

class StyledInputField(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(36)
        
    def update_style(self, theme):
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text']};
                border: 1px solid {theme['input_border']};
                border-radius: 4px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme['accent']};
            }}
        """)

class CardWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
    def update_style(self, theme):
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: {theme['card']};
                border: 1px solid {theme['card_border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

class GanttChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the main card for the Gantt chart
        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)
        
        # Create header with title
        header_layout = QHBoxLayout()
        chart_title = QLabel("Process Execution Timeline")
        chart_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(chart_title)
        header_layout.addStretch()
        
        # Add refresh button
        self.refresh_btn = StyledButton("Refresh Chart", is_primary=False)
        header_layout.addWidget(self.refresh_btn)
        
        card_layout.addLayout(header_layout)
        
        # Create the figure and canvas
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        card_layout.addWidget(self.canvas)
        
        # Set up the plot
        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.15, bottom=0.1, right=0.95, top=0.9)
        
        # Add the card to the main layout
        self.layout.addWidget(self.card)
        
    def update_chart(self, tasks, algorithm_name, execution_history=None):
        # Clear the previous plot
        self.ax.clear()
        
        if not tasks:
            return
        
        # Add a row for idle time
        idle_row = "Idle"
        
        # Handle Round Robin algorithm separately with execution history
        if algorithm_name == "RR" and execution_history:
            # Group by task ID
            task_rows = {}
            colors = {}
            
            # Generate a unique color for each task
            for task in tasks:
                # Use a more visually appealing color palette
                colors[task.id] = plt.cm.viridis(task.id / (len(tasks) + 1))
                task_rows[task.id] = f"P{task.id}"
            
            # Add idle row
            process_names = [idle_row] + [f"P{task.id}" for task in sorted(tasks, key=lambda x: x.id)]
            
            # Sort execution history by start time
            sorted_history = sorted(execution_history, key=lambda x: x['start_time'])
            
            # Find idle periods
            idle_periods = []
            prev_end_time = 0
            
            for segment in sorted_history:
                if segment['start_time'] > prev_end_time:
                    # There's an idle period
                    idle_periods.append({
                        'start_time': prev_end_time,
                        'end_time': segment['start_time']
                    })
                prev_end_time = segment['end_time']
            
            # Plot idle periods
            for period in idle_periods:
                self.ax.barh(idle_row, period['end_time'] - period['start_time'], 
                            left=period['start_time'], color='lightgray', 
                            alpha=0.7, edgecolor='white', linewidth=0.5)
                
                # Add "Idle" text if there's enough space
                if period['end_time'] - period['start_time'] > 0.5:
                    self.ax.text(period['start_time'] + (period['end_time'] - period['start_time'])/2, 
                                0, "Idle", ha='center', va='center', color='black')
            
            # Plot each execution segment
            for segment in sorted_history:
                task_id = segment['task_id']
                start_time = segment['start_time']
                duration = segment['end_time'] - segment['start_time']
                
                # Find the y position for this task
                y_pos = process_names.index(f"P{task_id}")
                
                # Draw the segment
                self.ax.barh(f"P{task_id}", duration, left=start_time, 
                            color=colors[task_id], alpha=0.9, edgecolor='white', linewidth=0.5)
                
                # Add text if there's enough space
                if duration > 0.5:
                    self.ax.text(start_time + duration/2, y_pos, 
                              f"P{task_id}", ha='center', va='center', color='white', fontweight='bold')
            
        else:
            # Original implementation for other algorithms with improved visuals and idle time
            sorted_tasks = sorted(tasks, key=lambda x: (x.completion_time - x.execution_time, x.id))
            process_names = [idle_row] + [f"P{task.id}" for task in sorted_tasks]
            
            # Create timeline of task execution
            timeline = []
            for task in sorted_tasks:
                start_time = task.completion_time - task.execution_time
                end_time = task.completion_time
                timeline.append({
                    'task_id': task.id,
                    'start_time': start_time,
                    'end_time': end_time
                })
            
            # Sort timeline by start time
            timeline.sort(key=lambda x: x['start_time'])
            
            # Find idle periods
            idle_periods = []
            current_time = 0
            
            for period in timeline:
                if period['start_time'] > current_time:
                    # There's an idle period
                    idle_periods.append({
                        'start_time': current_time,
                        'end_time': period['start_time']
                    })
                current_time = max(current_time, period['end_time'])
            
            # Plot idle periods
            for period in idle_periods:
                self.ax.barh(idle_row, period['end_time'] - period['start_time'], 
                            left=period['start_time'], color='lightgray', 
                            alpha=0.7, edgecolor='white', linewidth=0.5)
                
                # Add "Idle" text if there's enough space
                if period['end_time'] - period['start_time'] > 0.5:
                    self.ax.text(period['start_time'] + (period['end_time'] - period['start_time'])/2, 
                                0, "Idle", ha='center', va='center', color='black')
            
            # Plot execution periods
            colors = plt.cm.viridis(np.linspace(0, 1, len(sorted_tasks)))
            
            for i, task in enumerate(sorted_tasks):
                start_time = task.completion_time - task.execution_time
                duration = task.execution_time
                
                # Find the y position for this task
                y_pos = process_names.index(f"P{task.id}")
                
                # Draw the bar
                self.ax.barh(f"P{task.id}", duration, left=start_time, 
                           color=colors[i], alpha=0.9, edgecolor='white', linewidth=0.5)
                
                # Add text if there's enough space
                if duration > 0.5:
                    self.ax.text(start_time + duration/2, y_pos, 
                               f"P{task.id}", ha='center', va='center', color='white', fontweight='bold')
        
        # Set y-ticks
        self.ax.set_yticks(range(len(process_names)))
        self.ax.set_yticklabels(process_names)
        
        # Customize the plot
        self.ax.set_xlabel('Time Units', fontweight='bold')
        self.ax.set_ylabel('Process ID', fontweight='bold')
        self.ax.set_title(f'Process Execution Timeline - {algorithm_name}', fontsize=14, fontweight='bold')
        self.ax.grid(True, axis='x', linestyle='--', alpha=0.7)
        
        # Set x-axis ticks to show times
        if algorithm_name == "RR" and execution_history:
            max_time = max([segment['end_time'] for segment in execution_history])
        else:
            max_time = max([task.completion_time for task in tasks])
        
        # Create more intuitive tick marks
        ticks = np.arange(0, max_time + 2, max(1, int(max_time / 10)))
        self.ax.set_xticks(ticks)
        
        # Set better limits
        self.ax.set_xlim(0, max_time + 1)
        
        # Calculate efficiency metrics
        total_time = max_time
        busy_time = sum(task.execution_time for task in tasks)
        idle_time = total_time - busy_time
        utilization = (busy_time / total_time) * 100 if total_time > 0 else 0
        
        # Add a legend or summary with efficiency metrics
        summary_text = f"Algorithm: {algorithm_name}\n" \
                       f"Total Tasks: {len(tasks)}\n" \
                       f"Total Time: {max_time:.1f} units\n" \
                       f"CPU Utilization: {utilization:.1f}%\n" \
                       f"Idle Time: {idle_time:.1f} units"
        
        self.ax.text(0.02, 0.02, summary_text, transform=self.ax.transAxes, 
                   fontsize=9, verticalalignment='bottom', bbox=dict(boxstyle='round', alpha=0.1))
        
        # Refresh the canvas
        self.canvas.draw()
        
    def update_style(self, theme, is_dark_mode):
        self.card.update_style(theme)
        
        # Update matplotlib colors for dark/light mode
        if is_dark_mode:
            plt.style.use('dark_background')
            text_color = 'white'
        else:
            plt.style.use('default')  
            text_color = 'black'
            
        # Update text colors
        for text in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            text.set_color(text_color)
            
        self.ax.title.set_color(text_color)
        self.ax.xaxis.label.set_color(text_color)
        self.ax.yaxis.label.set_color(text_color)
        
        # Update grid color
        self.ax.grid(color=text_color, alpha=0.3)
        
        # Update the figure background
        self.figure.patch.set_facecolor(theme['gantt_bg'])
        self.ax.set_facecolor(theme['gantt_bg'])
        
        # Refresh
        self.canvas.draw()

class EnergySchedulerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Energy-Efficient CPU Scheduler")
        self.setGeometry(100, 100, 1280, 800)
        
        # Initialize theme
        self.current_theme = Themes.LIGHT
        self.is_dark_mode = False
        
        # Set up the central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        central_widget.setLayout(main_layout)
        
        # Create header with title and theme toggle
        header_layout = QHBoxLayout()
        app_title = QLabel("Energy-Efficient CPU Scheduler")
        app_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(app_title)
        
        header_layout.addStretch()
        
        # Theme toggle button
        self.theme_toggle = StyledButton("🌙 Dark Mode", is_primary=False)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.theme_toggle.setFixedWidth(120)
        header_layout.addWidget(self.theme_toggle)
        
        main_layout.addLayout(header_layout)
        
        # Create tab widget with custom styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)
        
        # Create input tab
        input_tab = QWidget()
        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)
        input_scroll.setWidget(input_tab)
        
        input_layout = QVBoxLayout()
        input_layout.setSpacing(16)
        input_tab.setLayout(input_layout)
        
        # Create task input card
        task_input_card = CardWidget()
        task_input_layout = QVBoxLayout(task_input_card)
        
        # Card title
        task_input_title = QLabel("Add New Task")
        task_input_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        task_input_layout.addWidget(task_input_title)
        
        # Input fields
        input_grid = QHBoxLayout()
        self.task_inputs = {}
        
        # Create input groups
        input_fields = [
            {"label": "Task ID", "placeholder": "Enter task ID"},
            {"label": "Arrival Time", "placeholder": "Enter arrival time"},
            {"label": "Execution Time", "placeholder": "Enter execution time"},
            {"label": "Priority", "placeholder": "Enter priority (lower = higher)"},
            {"label": "Energy Intensity", "placeholder": "Enter energy intensity (W)"},
            {"label": "CPU Demand", "placeholder": "Enter CPU demand (%)"}
        ]
        
        for field in input_fields:
            field_layout = QVBoxLayout()
            field_label = QLabel(field["label"])
            field_layout.addWidget(field_label)
            
            input_field = StyledInputField(field["placeholder"])
            self.task_inputs[field["label"]] = input_field
            field_layout.addWidget(input_field)
            
            input_grid.addLayout(field_layout)
        
        task_input_layout.addLayout(input_grid)
        
        # Add task button
        add_task_btn = StyledButton("Add Task", is_primary=True)
        add_task_btn.clicked.connect(self.add_task)
        add_task_btn.setFixedWidth(150)
        add_task_btn_layout = QHBoxLayout()
        add_task_btn_layout.addStretch()
        add_task_btn_layout.addWidget(add_task_btn)
        task_input_layout.addLayout(add_task_btn_layout)
        
        input_layout.addWidget(task_input_card)
        
        # Tasks table card
        tasks_table_card = CardWidget()
        tasks_table_layout = QVBoxLayout(tasks_table_card)
        
        # Card title with action buttons
        table_header_layout = QHBoxLayout()
        tasks_table_title = QLabel("Task Queue")
        tasks_table_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        table_header_layout.addWidget(tasks_table_title)
        
        table_header_layout.addStretch()
        
        clear_tasks_btn = StyledButton("Clear All Tasks", is_primary=False)
        clear_tasks_btn.clicked.connect(self.clear_tasks)
        table_header_layout.addWidget(clear_tasks_btn)
        
        tasks_table_layout.addLayout(table_header_layout)
        
        # Enhanced table for tasks
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(9)
        self.tasks_table.setHorizontalHeaderLabels([
            "Task ID", "Arrival Time", "Execution Time", "Priority", 
            "Energy", "CPU Demand", "Completion", "Turnaround", "Waiting"
        ])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tasks_table_layout.addWidget(self.tasks_table)
        
        input_layout.addWidget(tasks_table_card)
        
        # Create a horizontal layout for the three cards
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)
        
        # 1. Algorithm control card
        algo_card = CardWidget()
        algo_layout = QVBoxLayout(algo_card)
        
        # Card title
        algo_title = QLabel("Scheduling Algorithms")
        algo_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        algo_layout.addWidget(algo_title)
        
        # Algorithm buttons in a vertical layout now (for column)
        algo_btn_layout = QVBoxLayout()
        
        # Create algorithm buttons with icons
        self.sjf_btn = StyledButton("Shortest Job First", is_primary=True)
        self.fcfs_btn = StyledButton("First Come First Served", is_primary=True)
        self.rr_btn = StyledButton("Round Robin", is_primary=True)
        self.priority_btn = StyledButton("Priority-Based", is_primary=True)
        
        # Connect button signals
        self.sjf_btn.clicked.connect(lambda: self.run_algorithm("SJF"))
        self.fcfs_btn.clicked.connect(lambda: self.run_algorithm("FCFS"))
        self.rr_btn.clicked.connect(lambda: self.run_algorithm("RR"))
        self.priority_btn.clicked.connect(lambda: self.run_algorithm("Priority"))
        
        # Add buttons to layout
        algo_btn_layout.addWidget(self.sjf_btn)
        algo_btn_layout.addWidget(self.fcfs_btn)
        algo_btn_layout.addWidget(self.rr_btn)
        algo_btn_layout.addWidget(self.priority_btn)
        
        algo_layout.addLayout(algo_btn_layout)
        
        # 2. Results summary card
        results_card = CardWidget()
        results_layout = QVBoxLayout(results_card)
        
        # Card title
        results_title = QLabel("Energy Consumption Results")
        results_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        results_layout.addWidget(results_title)
        
        # Energy display
        energy_layout = QVBoxLayout()
        energy_label = QLabel("Total Energy Consumed:")
        energy_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        energy_layout.addWidget(energy_label)
        
        self.energy_consumed_box = StyledInputField()
        self.energy_consumed_box.setReadOnly(True)
        self.energy_consumed_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        energy_layout.addWidget(self.energy_consumed_box)
        
        results_layout.addLayout(energy_layout)
        results_layout.addStretch()
        
        # 3. AI advisor card
        ai_card = CardWidget()
        ai_layout = QVBoxLayout(ai_card)
        
        # Card title with action button
        ai_title = QLabel("AI Advisor")
        ai_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        ai_layout.addWidget(ai_title)
        
        check_ai_btn = StyledButton("Ask AI for Recommendations", is_primary=True)
        check_ai_btn.clicked.connect(self.check_with_ai)
        ai_layout.addWidget(check_ai_btn)
        
        # AI response text area
        self.ai_response_box = QTextEdit()
        self.ai_response_box.setReadOnly(True)
        self.ai_response_box.setPlaceholderText("AI recommendations will appear here...")
        ai_layout.addWidget(self.ai_response_box)
        
        # Add the three cards to the horizontal layout
        controls_layout.addWidget(algo_card, 1)
        controls_layout.addWidget(results_card, 1)
        controls_layout.addWidget(ai_card, 2)  # Give AI advisor more space
        
        # Add the horizontal layout to the main layout
        input_layout.addLayout(controls_layout)
        
        # Create Gantt chart tab
        self.gantt_tab = QWidget()
        gantt_layout = QVBoxLayout()
        gantt_layout.setContentsMargins(0, 0, 0, 0)
        self.gantt_tab.setLayout(gantt_layout)
        
        self.gantt_widget = GanttChartWidget()
        gantt_layout.addWidget(self.gantt_widget)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(input_scroll, "Task Management")
        self.tab_widget.addTab(self.gantt_tab, "Visualization")
        
        # Connect refresh button
        self.gantt_widget.refresh_btn.clicked.connect(self.update_gantt_chart)
        
        self.tasks = []
        self.current_algorithm = None
        
        # Apply initial theme
        self.apply_theme()
    
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.current_theme = Themes.DARK
            self.theme_toggle.setText("☀️ Light Mode")
        else:
            self.current_theme = Themes.LIGHT
            self.theme_toggle.setText("🌙 Dark Mode")
        
        self.apply_theme()
    
    def apply_theme(self):
        # Apply theme to the main window
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.current_theme['window']};
                color: {self.current_theme['text']};
                font-family: Arial;
            }}
            QTabWidget::pane {{
                border: 1px solid {self.current_theme['card_border']};
                border-radius: 4px;
                padding: 0px;
            }}
            QTabBar::tab {{
                background-color: {self.current_theme['card']};
                color: {self.current_theme['text']};
                border: 1px solid {self.current_theme['card_border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.current_theme['accent']};
                color: {self.current_theme['button_text']};
                font-weight: bold;
            }}
            QTableWidget {{
                background-color: {self.current_theme['card']};
                alternate-background-color: {self.current_theme['table_row_alt']};
                gridline-color: {self.current_theme['card_border']};
                selection-background-color: {self.current_theme['accent']};
                selection-color: {self.current_theme['button_text']};
            }}
            QHeaderView::section {{
                background-color: {self.current_theme['table_header']};
                color: {self.current_theme['text']};
                padding: 5px;
                border: 1px solid {self.current_theme['card_border']};
            }}
            QTextEdit {{
                background-color: {self.current_theme['input_bg']};
                color: {self.current_theme['text']};
                border: 1px solid {self.current_theme['input_border']};
                border-radius: 4px;
                padding: 8px;
            }}
            QScrollBar {{
                background-color: {self.current_theme['input_bg']};
            }}
            QScrollBar::handle {{
                background-color: {self.current_theme['input_border']};
                border-radius: 4px;
            }}
        """)
        
        # Update theme for styled components
        self.theme_toggle.update_style(self.current_theme)
        self.sjf_btn.update_style(self.current_theme)
        self.fcfs_btn.update_style(self.current_theme)
        self.rr_btn.update_style(self.current_theme)
        self.priority_btn.update_style(self.current_theme)
        self.gantt_widget.refresh_btn.update_style(self.current_theme)
        
        # Update input fields
        for input_field in self.task_inputs.values():
            input_field.update_style(self.current_theme)
        
        self.energy_consumed_box.update_style(self.current_theme)
        
        # Update card widgets
        for card in self.findChildren(CardWidget):
            card.update_style(self.current_theme)
            
        # Update gantt chart
        self.gantt_widget.update_style(self.current_theme, self.is_dark_mode)
    
    def add_task(self):
        try:
            task_id = int(self.task_inputs["Task ID"].text())
            
            # Check if a task with this ID already exists
            existing_task_index = None
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    existing_task_index = i
                    break
            
            # Create task with the input values
            task = Task(
                id=task_id,
                arrival_time=float(self.task_inputs["Arrival Time"].text()),
                execution_time=float(self.task_inputs["Execution Time"].text()),
                priority=float(self.task_inputs["Priority"].text()),
                energy_intensity=float(self.task_inputs["Energy Intensity"].text()),
                cpu_demand=float(self.task_inputs["CPU Demand"].text())
            )
            
            if existing_task_index is not None:
                # Update existing task in the list
                self.tasks[existing_task_index] = task
                
                # Update the row in the table
                row_position = None
                for row in range(self.tasks_table.rowCount()):
                    if int(self.tasks_table.item(row, 0).text()) == task_id:
                        row_position = row
                        break
                        
                # Update task properties in the table
                for col, value in enumerate([task.id, task.arrival_time, task.execution_time, 
                                            task.priority, task.energy_intensity, task.cpu_demand]):
                    self.tasks_table.setItem(row_position, col, QTableWidgetItem(str(value)))
                
                # Clear CT, TAT, WT columns for the updated task
                for col in range(6, 9):
                    self.tasks_table.setItem(row_position, col, QTableWidgetItem(""))
                    
                QMessageBox.information(self, "Task Updated", f"Task with ID {task_id} has been updated.")
            else:
                # Add new task to the list
                self.tasks.append(task)
                
                # Add new row to the table
                row_position = self.tasks_table.rowCount()
                self.tasks_table.insertRow(row_position)
                
                # Add task properties to the table
                for col, value in enumerate([task.id, task.arrival_time, task.execution_time, 
                                            task.priority, task.energy_intensity, task.cpu_demand]):
                    self.tasks_table.setItem(row_position, col, QTableWidgetItem(str(value)))
                    
                # Leave CT, TAT, WT columns empty
                for col in range(6, 9):
                    self.tasks_table.setItem(row_position, col, QTableWidgetItem(""))
            
            # Clear input fields
            for input_field in self.task_inputs.values():
                input_field.clear()
                
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for all fields.")
    
    def run_algorithm(self, algorithm):
        if not self.tasks:
            QMessageBox.warning(self, "Algorithm Error", "Please add tasks before running algorithms.")
            return
        
        self.current_algorithm = algorithm
        
        # Create a copy of tasks for scheduling
        tasks_copy = self.tasks.copy()
        
        # Sort tasks by arrival time initially
        tasks_copy.sort(key=lambda x: x.arrival_time)
        
        if algorithm == "FCFS":
            self.schedule_fcfs(tasks_copy)
        elif algorithm == "SJF":
            self.schedule_sjf(tasks_copy)
        elif algorithm == "RR":
            # Ask for time quantum using proper input dialog
            time_quantum, ok = QInputDialog.getDouble(
                self, 
                "Round Robin Time Quantum", 
                "Enter time quantum:", 
                2.0, 0.1, 100.0, 1
            )
            if ok:
                self.schedule_round_robin(tasks_copy, time_quantum)
            else:
                return  # User cancelled the dialog
        elif algorithm == "Priority":
            self.schedule_priority(tasks_copy)
            
        # Update results in the table
        self.display_results()
        
        # Update Gantt chart
        self.update_gantt_chart()
        
        # Switch to Gantt chart tab
        self.tab_widget.setCurrentIndex(1)
    
    def update_gantt_chart(self):
        if not self.tasks or not self.current_algorithm:
            QMessageBox.warning(self, "Gantt Chart Error", "Please run an algorithm before viewing the Gantt chart.")
            return
        
        # Update the Gantt chart
        if self.current_algorithm == "RR" and hasattr(self, 'execution_history'):
            self.gantt_widget.update_chart(self.tasks, self.current_algorithm, self.execution_history)
        else:
            self.gantt_widget.update_chart(self.tasks, self.current_algorithm)
    
    def schedule_fcfs(self, tasks):
        current_time = 0
        
        for task in tasks:
            # If arrival time is after current time, update current time
            if task.arrival_time > current_time:
                current_time = task.arrival_time
            
            # Calculate completion time
            current_time += task.execution_time
            task.completion_time = current_time
            
            # Calculate turnaround time and waiting time
            task.turnaround_time = task.completion_time - task.arrival_time
            task.waiting_time = task.turnaround_time - task.execution_time
            
        # Calculate total energy consumption
        total_energy = sum(task.execution_time * task.energy_intensity for task in tasks)
        self.energy_consumed_box.setText(f"{total_energy:.4f} Wh")
    
    def schedule_sjf(self, tasks):
        current_time = 0
        remaining_tasks = tasks.copy()
        completed_tasks = []
        
        while remaining_tasks:
            # Find available tasks
            available_tasks = [t for t in remaining_tasks if t.arrival_time <= current_time]
            
            if not available_tasks:
                # No task available, move time to next arrival
                current_time = min(t.arrival_time for t in remaining_tasks)
                continue
            
            # Find shortest job among available tasks
            next_task = min(available_tasks, key=lambda t: t.execution_time)
            
            # Execute task
            current_time += next_task.execution_time
            next_task.completion_time = current_time
            next_task.turnaround_time = next_task.completion_time - next_task.arrival_time
            next_task.waiting_time = next_task.turnaround_time - next_task.execution_time
            
            # Move task to completed
            remaining_tasks.remove(next_task)
            completed_tasks.append(next_task)
        
        # Update original tasks with calculated metrics
        for original_task in self.tasks:
            for completed_task in completed_tasks:
                if original_task.id == completed_task.id:
                    original_task.completion_time = completed_task.completion_time
                    original_task.turnaround_time = completed_task.turnaround_time
                    original_task.waiting_time = completed_task.waiting_time
        
        # Calculate total energy consumption
        total_energy = sum(task.execution_time * task.energy_intensity for task in tasks)
        self.energy_consumed_box.setText(f"{total_energy:.4f} Wh")
    
    def schedule_round_robin(self, tasks, time_quantum=2.0):
        # Track current time
        current_time = 0
        
        # Create a dictionary to store the execution history for Gantt chart
        execution_history = []
        
        # Create a dictionary to store remaining execution time
        remaining_time = {task.id: task.execution_time for task in tasks}
        completed = {task.id: False for task in tasks}
        
        # Initialize completion times
        completion_times = {task.id: 0 for task in tasks}
        
        # Processing queue
        queue = []
        
        while True:
            # Check if all tasks are completed
            if all(completed.values()):
                break
                
            # Add newly arrived tasks to queue
            for task in tasks:
                if not completed[task.id] and task.arrival_time <= current_time and task.id not in [t.id for t in queue]:
                    queue.append(task)
            
            # If queue is empty, advance time to next arrival
            if not queue:
                # Find tasks that haven't arrived yet
                not_arrived = [task for task in tasks if not completed[task.id] and task.arrival_time > current_time]
                if not_arrived:
                    next_arrival = min([task.arrival_time for task in not_arrived])
                    current_time = next_arrival
                    continue
                else:
                    # If there are no tasks left to arrive, we're done
                    break
            
            # Get next task from queue
            current_task = queue.pop(0)
            
            # Process for time quantum or until completion
            execution_slice = min(time_quantum, remaining_time[current_task.id])
            
            # Record execution history for Gantt chart
            execution_history.append({
                'task_id': current_task.id,
                'start_time': current_time,
                'end_time': current_time + execution_slice
            })
            
            # Update current time after execution
            current_time += execution_slice
            remaining_time[current_task.id] -= execution_slice
            
            # Check if task is completed
            if remaining_time[current_task.id] <= 0.001:  # Use small threshold for floating point comparison
                completed[current_task.id] = True
                completion_times[current_task.id] = current_time
            else:
                # Add newly arrived tasks to queue before re-adding current task
                for task in tasks:
                    if not completed[task.id] and task.arrival_time <= current_time and task.id not in [t.id for t in queue] and task.id != current_task.id:
                        queue.append(task)
                # Re-add current task to the end of the queue
                queue.append(current_task)
        
        # Store execution history for Gantt chart use
        self.execution_history = execution_history
        
        # Update tasks with calculated metrics
        for task in self.tasks:
            task.completion_time = completion_times[task.id]
            task.turnaround_time = task.completion_time - task.arrival_time
            task.waiting_time = task.turnaround_time - task.execution_time
            
        # Calculate total energy consumption
        total_energy = sum(task.execution_time * task.energy_intensity for task in tasks)
        self.energy_consumed_box.setText(f"{total_energy:.4f} Wh")
    
    def schedule_priority(self, tasks):
        current_time = 0
        remaining_tasks = tasks.copy()
        completed_tasks = []
        
        while remaining_tasks:
            # Find available tasks
            available_tasks = [t for t in remaining_tasks if t.arrival_time <= current_time]
            
            if not available_tasks:
                # No task available, move time to next arrival
                current_time = min(t.arrival_time for t in remaining_tasks)
                continue
            
            # Find highest priority (lower number means higher priority)
            next_task = min(available_tasks, key=lambda t: t.priority)
            
            # Execute task
            current_time += next_task.execution_time
            next_task.completion_time = current_time
            next_task.turnaround_time = next_task.completion_time - next_task.arrival_time
            next_task.waiting_time = next_task.turnaround_time - next_task.execution_time
            
            # Move task to completed
            remaining_tasks.remove(next_task)
            completed_tasks.append(next_task)
        
        # Update original tasks with calculated metrics
        for original_task in self.tasks:
            for completed_task in completed_tasks:
                if original_task.id == completed_task.id:
                    original_task.completion_time = completed_task.completion_time
                    original_task.turnaround_time = completed_task.turnaround_time
                    original_task.waiting_time = completed_task.waiting_time
        
        # Calculate total energy consumption
        total_energy = sum(task.execution_time * task.energy_intensity for task in tasks)
        self.energy_consumed_box.setText(f"{total_energy:.4f} Wh")
    
    def display_results(self):
        # Update the existing task table with results
        for row, task in enumerate(self.tasks):
            # Find the row for this task ID
            for i in range(self.tasks_table.rowCount()):
                if str(self.tasks_table.item(i, 0).text()) == str(task.id):
                    # Update CT, TAT, WT columns (columns 6, 7, 8)
                    self.tasks_table.setItem(i, 6, QTableWidgetItem(f"{task.completion_time:.2f}"))
                    self.tasks_table.setItem(i, 7, QTableWidgetItem(f"{task.turnaround_time:.2f}"))
                    self.tasks_table.setItem(i, 8, QTableWidgetItem(f"{task.waiting_time:.2f}"))
                    break
        
        # Add or update average row
        # Check if average row already exists
        has_average_row = False
        average_row_index = -1
        for i in range(self.tasks_table.rowCount()):
            if self.tasks_table.item(i, 0) and self.tasks_table.item(i, 0).text() == "Average":
                has_average_row = True
                average_row_index = i
                break
                
        # Calculate averages
        avg_turnaround = sum(task.turnaround_time for task in self.tasks) / len(self.tasks)
        avg_waiting = sum(task.waiting_time for task in self.tasks) / len(self.tasks)
        
        if has_average_row:
            # Update existing average row
            self.tasks_table.setItem(average_row_index, 7, QTableWidgetItem(f"{avg_turnaround:.2f}"))
            self.tasks_table.setItem(average_row_index, 8, QTableWidgetItem(f"{avg_waiting:.2f}"))
        else:
            # Add new average row
            row_position = self.tasks_table.rowCount()
            self.tasks_table.insertRow(row_position)
            self.tasks_table.setItem(row_position, 0, QTableWidgetItem("Average"))
            # Leave empty cells for non-applicable columns
            for col in range(1, 6):
                self.tasks_table.setItem(row_position, col, QTableWidgetItem(""))
            # Skip completion time column
            self.tasks_table.setItem(row_position, 6, QTableWidgetItem(""))
            # Set average TAT and WT
            self.tasks_table.setItem(row_position, 7, QTableWidgetItem(f"{avg_turnaround:.2f}"))
            self.tasks_table.setItem(row_position, 8, QTableWidgetItem(f"{avg_waiting:.2f}"))
        
        QMessageBox.information(self, "Algorithm Completed", 
                               f"{self.current_algorithm} scheduling completed successfully!")
    
    def clear_tasks(self):
        self.tasks.clear()
        self.tasks_table.setRowCount(0)
        self.energy_consumed_box.clear()
        
        # Clear the Gantt chart
        self.gantt_widget.ax.clear()
        self.gantt_widget.canvas.draw()
    
    def check_with_ai(self):
        if not self.tasks:
            QMessageBox.warning(self, "AI Check Error", "Please add tasks before checking with AI.")
            return
            
        task_data = [
            {
                "Task ID": task.id,
                "Arrival Time": task.arrival_time,
                "Execution Time": task.execution_time,
                "Priority": task.priority,
                "Energy Intensity": task.energy_intensity,
                "CPU Demand": task.cpu_demand
            } for task in self.tasks
        ]
        
        prompt = f"""
        Given the following task data:
        {task_data}
        just suggest one best algo suited for these tasks out of (sjf,fcfs,priority,round-robin) based on energy consumed
        """
        
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            if response and hasattr(response, "text"):
                self.ai_response_box.setText(response.text)
            else:
                self.ai_response_box.setText("Error: No valid response from AI.")
        except Exception as e:
            self.ai_response_box.setText(f"AI Error: {str(e)}")

def main():
    app = QApplication(sys.argv)
    gui = EnergySchedulerGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
