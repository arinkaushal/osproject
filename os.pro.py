import sys
import psutil
import google.generativeai as genai
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

API_KEY = "AIzaSyCxC5CUgTq9ggXTtUZp0Nd9gDaHxr-bf_A"
genai.configure(api_key=API_KEY)

class FetchProcessesThread(QThread):
    result_signal = pyqtSignal(list)
    
    def run(self):
        process_data = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'num_threads']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    num_threads = proc.info['num_threads']
                    

                    try:
                        cpu_usages = []
                        for _ in range(3):
                            cpu_usage = proc.cpu_percent(interval=0.1)
                            cpu_usages.append(cpu_usage)
                        
                        cpu_usage = max(cpu_usages)
                    except Exception as e:
                        print(f"CPU usage error for {name}: {e}")
                        cpu_usage = 0.0
                    
                    with proc.oneshot():
                        status = proc.status()
                        memory_usage = proc.memory_info().rss // (1024 * 1024)  # in MB
                        
                        try:
                            allocated_resources = f"File Handles: {len(proc.open_files())}" if proc.open_files() else "None"
                        except Exception:
                            allocated_resources = "Unable to count file handles"
                        
                        requested_resources = f"Memory: {memory_usage}MB, CPU: {cpu_usage}%"
                        
                        process_data.append({
                            'pid': pid,
                            'name': name,
                            'status': status,
                            'num_threads': num_threads,
                            'memory_usage': memory_usage,
                            'cpu_usage': cpu_usage,
                            'allocated_resources': allocated_resources,
                            'requested_resources': requested_resources
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        
        except Exception as e:
            print(f"Error in process collection: {e}")
        
        process_data.sort(key=lambda x: x['cpu_usage'], reverse=True)
        
        self.result_signal.emit(process_data)
        
class DeadlockDetectionThread(QThread):
    result_signal = pyqtSignal(str)
    
    def __init__(self, process_data):
        super().__init__()
        self.process_data = process_data
    
    def run(self):
        try:
            prompt = "Given the following process allocation and request information, identify if there is a deadlock:\n" + \
                     "Process Information:\n" + \
                     "\n".join([f"PID: {proc['pid']}, Name: {proc['name']}, Status: {proc['status']}, Threads: {proc['num_threads']}, " +
                                f"Memory Usage: {proc['memory_usage']}MB, CPU Usage: {proc['cpu_usage']}%, " +
                                f"Allocated Resources: {proc['allocated_resources']}, Requested Resources: {proc['requested_resources']}" 
                                for proc in self.process_data])
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            self.result_signal.emit(response.text)
        except Exception as e:
            self.result_signal.emit(f"Error: {str(e)}")


class DeadlockDetectorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("⚙️ AI Deadlock Detector 🔍")
        self.setGeometry(100, 100, 1400, 700)
        self.setStyleSheet("background-color: #000000; color: white;")

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        
        


        self.process_table = QTableWidget()
        self.process_table.setColumnCount(8)  
        self.process_table.setHorizontalHeaderLabels([
            " 🔢 S.No ", 
            " 🆔 PID ", 
            " 📝 Process Name ", 
            " ⚡ Status ", 
            " 🧵 Number of Threads ", 
            " 💾 Memory Usage ",
            " 📦 Allocated Resources ", 
            " 📥 Requested Resources "
        ])
        self.process_table.setStyleSheet("background-color: #222; color: white;")
        self.process_table.resizeColumnsToContents()
        left_layout.addWidget(self.process_table)
        
        
        self.get_process_button = QPushButton("🔄 Fetch Processes")
        self.get_process_button.setStyleSheet("background-color: #0275d8; color: white; font-weight: bold; padding: 8px;")
        self.get_process_button.clicked.connect(self.fetch_processes)
        left_layout.addWidget(self.get_process_button)
        
        self.loading_bar = QProgressBar()
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setRange(0, 0)
        self.loading_bar.hide()
        left_layout.addWidget(self.loading_bar)
        
        self.figure, self.ax_threads = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        left_layout.addWidget(self.canvas)
        
        self.show_graph_button = QPushButton("📊 Show Graph Allocation")
        self.show_graph_button.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 8px;")
        self.show_graph_button.clicked.connect(self.manual_graph_update)
        left_layout.addWidget(self.show_graph_button)
        
        self.detect_deadlock_button = QPushButton("🚨 Detect Deadlock")
        self.detect_deadlock_button.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 8px;")
        self.detect_deadlock_button.clicked.connect(self.detect_deadlock)
        right_layout.addWidget(self.detect_deadlock_button)
        
        self.deadlock_response = QTextEdit()
        self.deadlock_response.setReadOnly(True)
        self.deadlock_response.setStyleSheet("background-color: #222; color: white;")
        right_layout.addWidget(self.deadlock_response)
        
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)
    
    def fetch_processes(self):
        self.loading_bar.show()
        QApplication.processEvents()
        self.process_thread = FetchProcessesThread()
        self.process_thread.result_signal.connect(self.update_process_table)
        self.process_thread.start()
    
    def update_process_table(self, process_data):
        self.loading_bar.hide()
        self.process_table.setRowCount(0)
        for i, proc in enumerate(process_data):  # Remove the [-30:] slice to show all processes
            row = self.process_table.rowCount()
            self.process_table.insertRow(row)
            self.process_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.process_table.setItem(row, 1, QTableWidgetItem(str(proc['pid'])))
            self.process_table.setItem(row, 2, QTableWidgetItem(proc['name']))
            self.process_table.setItem(row, 3, QTableWidgetItem(proc['status']))
            self.process_table.setItem(row, 4, QTableWidgetItem(str(proc['num_threads'])))
            self.process_table.setItem(row, 5, QTableWidgetItem(f"{proc['memory_usage']} MB"))
            self.process_table.setItem(row, 7, QTableWidgetItem(proc['allocated_resources']))
            self.process_table.setItem(row, 8, QTableWidgetItem(proc['requested_resources']))
    
    def manual_graph_update(self):
        self.ax_threads.clear()
        
        # Get last 10 processes
        last_10_processes = self.process_table.rowCount()
        start_index = max(0, last_10_processes - 10)
        
        process_names = [
            self.process_table.item(i, 2).text() 
            for i in range(start_index, last_10_processes)
        ]
        
        cpu_usages = [
            float(self.process_table.item(i, 6).text().replace('%', '')) 
            for i in range(start_index, last_10_processes)
        ]
        
        self.ax_threads.barh(process_names, cpu_usages, color='cyan')
        self.ax_threads.set_xlabel("CPU Usage (%)")
        self.ax_threads.set_title("Top Processes by CPU Usage")
        
        self.ax_threads.set_xlim(0, max(cpu_usages) * 1.1)
        
        self.canvas.draw()
        
    def detect_deadlock(self):
        try:
            if self.process_table.rowCount() == 0:
                self.deadlock_response.setText("Please fetch processes first.")
                return

            process_data = []
            for i in range(self.process_table.rowCount()):
                try:
                    proc_dict = {
                        'pid': self.process_table.item(i, 1).text(),
                        'name': self.process_table.item(i, 2).text(),
                        'status': self.process_table.item(i, 3).text(),
                        'num_threads': self.process_table.item(i, 4).text(),
                        'memory_usage': self.process_table.item(i, 5).text(),
                        'cpu_usage': self.process_table.item(i, 6).text(),
                        'allocated_resources': self.process_table.item(i, 7).text(),
                        'requested_resources': self.process_table.item(i, 8).text()
                    }
                    process_data.append(proc_dict)
                except Exception as e:
                    print(f"Error processing row {i}: {e}")

            if not process_data:
                self.deadlock_response.setText("No valid process data to analyze.")
                return

            self.deadlock_response.setText("Analyzing processes for potential deadlocks...")
            self.deadlock_thread = DeadlockDetectionThread(process_data)
            self.deadlock_thread.result_signal.connect(self.deadlock_response.setText)
            self.deadlock_thread.start()

        except Exception as e:
            self.deadlock_response.setText(f"Error in deadlock detection: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = DeadlockDetectorGUI()
    gui.show()
    sys.exit(app.exec())
