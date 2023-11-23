import csv
import requests
import ipaddress
import importlib
import glob
import os
import logging
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QCheckBox, QLineEdit, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def import_required_packages():
    required_packages = [
        'PyQt5', 'requests'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        missing = ", ".join(missing_packages)
        print(f"Missing packages: {missing}")
        print("\nTo install missing packages, use: pip install " + ' '.join(missing_packages))
        print("Note: On some Linux distributions, use 'pip3' instead of 'pip'.")
        print("On Archlinux, consider using 'pipx', installable via 'pacman' or 'pamac'.")
        sys.exit()

import_required_packages()

def is_private_ip(ip):
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        logging.error(f"Invalid IP address: {ip}")
        return False

def load_plugins(plugin_folder='plugins'):
    plugins = {}
    plugin_dir = os.path.join(os.path.dirname(__file__), plugin_folder)

    for py_file in glob.glob(os.path.join(plugin_dir, '*.py')):
        plugin_base_name = os.path.basename(py_file)[:-3]
        plugin_path = os.path.relpath(py_file, os.path.dirname(__file__))
        plugin_name = plugin_path.replace(os.sep, '.')[:-3]
        plugins[plugin_base_name] = {'type': 'python', 'name': plugin_name}

    return plugins

def execute_plugin(plugin, ip_address, command_flag=None):
    try:
        if plugin['type'] == 'python':
            plugin_module = importlib.import_module(plugin['name'])
            if command_flag:
                return True, plugin_module.run(ip_address, command_flag)
            else:
                return True, plugin_module.run(ip_address)
    except Exception as e:
        logging.error(f"Error executing plugin {plugin['name']} for IP {ip_address}: {e}")
        return False, str(e)

class IPFetcher(QThread):
    ip_fetched = pyqtSignal(str)

    def run(self):
        try:
            response = requests.get('https://httpbin.org/ip')
            ip = response.json().get('origin')
            self.ip_fetched.emit(ip)
        except Exception as e:
            self.ip_fetched.emit(f"Error: {e}")

class CsvWorker(QThread):
    update_status = pyqtSignal(str, str, int, int)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, input_file, plugins, output_file, command_flags):
        super().__init__()
        self.input_file = input_file
        self.plugins = plugins
        self.output_file = output_file
        self.command_flags = command_flags

    def run(self):
        plugin_name = "DefaultPlugin"        
        try:
            with open(self.input_file, newline='') as infile, open(self.output_file, 'w', newline='') as outfile:
                reader = list(csv.reader(infile))
                total_lines = len(reader)
                writer = csv.writer(outfile)

                for current_line, row in enumerate(reader, 1):
                    logging.debug(f"Processing line {current_line}: {row}")
                    ip = None
                    self.update_status.emit(plugin_name, ip, current_line, total_lines)
                    new_row = row.copy()
                    for ip in row:
                        if is_private_ip(ip):
                            self.update_status.emit("Skipping", ip, current_line, total_lines)
                            continue
                        for plugin_name, plugin in self.plugins.items():
                            command_flag = self.command_flags.get(plugin_name, "")  # Retrieve command flag here
                            self.update_status.emit(plugin_name, ip, current_line, total_lines)
                            success, result = execute_plugin(plugin, ip, command_flag)
                            if not success:
                                self.error_occurred.emit(result)
                            new_row.append(result if success else "Error")
                    writer.writerow(new_row)

            self.finished.emit()
        except Exception as e:
            logging.error(f"Error in CsvWorker: {e}")
            self.error_occurred.emit(f"CsvWorker Error: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mass IP Analysis')
        self.setMinimumSize(500, 400)  # Allow the window to be resized

        self.selected_output_file = None
        self.plugins = load_plugins('plugins')  # Load plugins from the 'plugins' folder

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Plugin layouts
        self.checkboxes = {}
        self.command_flags = {}
        for plugin_name in self.plugins.keys():
            checkbox = QCheckBox(plugin_name)
            command_flag_input = QLineEdit()
            self.checkboxes[plugin_name] = checkbox
            self.command_flags[plugin_name] = command_flag_input

            plugin_layout = QHBoxLayout()
            plugin_layout.addWidget(checkbox)
            plugin_layout.addWidget(command_flag_input)
            main_layout.addLayout(plugin_layout)

        # File selection setup
        self.file_path_label = QLabel('No file selected for analysis')
        self.file_path_button = QPushButton('Select File for Analysis')
        self.file_path_button.clicked.connect(self.select_analysis_file)
        main_layout.addWidget(self.file_path_label)
        main_layout.addWidget(self.file_path_button)

        self.output_file_label = QLabel('No file selected for output!')
        self.output_file_button = QPushButton('Select File for Output')
        self.output_file_button.clicked.connect(self.select_output_file)
        main_layout.addWidget(self.output_file_label)
        main_layout.addWidget(self.output_file_button)

        # Analysis button setup
        self.analysis_button = QPushButton('Start Analysis')
        self.analysis_button.clicked.connect(self.start_analysis)
        self.analysis_button.setEnabled(False)
        main_layout.addWidget(self.analysis_button)

        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)

        # Status labels
        self.status_label = QLabel("Ready")
        self.error_label = QLabel("")
        self.ip_status_label = QLabel("Fetching IP address...")

        # Styling for error messages
        self.error_label.setStyleSheet("color: red")

        # Add labels to the status bar layout
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.error_label)
        status_layout.addWidget(self.ip_status_label)

        # Set up the status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.addPermanentWidget(status_widget, 1)

        # Worker threads list
        self.worker_threads = []

        # Start IP fetcher thread
        self.ip_fetcher = IPFetcher()
        self.ip_fetcher.ip_fetched.connect(self.update_ip_status)
        self.ip_fetcher.start()

    def update_ip_status(self, ip):
        self.ip_status_label.setText(f"Current IP: {ip}")

    def select_analysis_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, 'Open Files')

        if file_paths:
            self.file_paths = file_paths  # Save selected file paths
            self.file_path_label.setText(', '.join(file_paths))  # Show selected file paths
            self.analysis_button.setEnabled(True)



    def select_output_file(self):
        logging.debug('select_output_file function called. Opening file dialog for output file selection.')
        
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save File', '', 'CSV Files (*.csv)')
        
        if file_path:
            self.selected_output_file = file_path
            self.output_file_label.setText(file_path)
            logging.debug(f'Output file selected: {file_path}')


        else:
            logging.debug('Output file selection was canceled by the user.')
            self.output_file_label.setText('No file selected for output!')

    def handle_plugin_error(self, error_message):
        logging.debug(f"Error occurred with a plugin, error message: {error_message}")
        self.error_label.setText(error_message)

    def start_analysis(self):
        selected_plugins = {name: plugin for name, plugin in self.plugins.items() if self.checkboxes[name].isChecked()}
        if not selected_plugins:
            QMessageBox.warning(self, 'Warning', 'No plugins selected for analysis.')
            return

        # Set default output file if none selected
        if not self.selected_output_file:
            self.selected_output_file = os.path.join(os.path.dirname(__file__), 'output.csv')
            logging.debug(f"No output file selected. Using default: {self.selected_output_file}")

        # Fetch command flags for each plugin
        command_flags = {name: self.command_flags[name].text() for name in self.plugins.keys()}

        self.worker_threads = [thread for thread in self.worker_threads if thread.isRunning()]

        for file_path in self.file_paths:
            worker = CsvWorker(file_path, selected_plugins, self.selected_output_file, command_flags)
            worker.update_status.connect(self.update_status_message)
            worker.error_occurred.connect(self.handle_plugin_error)
            worker.finished.connect(self.handle_finished_worker)  # Ensure this connection is made
            worker.start()
            self.worker_threads.append(worker) 



    def update_status_message(self, plugin_name, ip, current_line, total_lines):
        status_message = f"Processing {plugin_name} on {ip} (Line {current_line} of {total_lines})"
        self.status_label.setText(status_message)


    def handle_finished_worker(self):
        worker = self.sender()
        if worker:
            worker.deleteLater()  # Safely delete the worker
        # Refresh the worker_threads list to only keep running threads
        self.worker_threads = [thread for thread in self.worker_threads if thread.isRunning()]
        # Now check if all threads have finished
        if not self.worker_threads:
            self.status_label.setText("Analysis completed!")  # Update the status label

    def closeEvent(self, event):
            for worker in self.worker_threads:
                if worker.isRunning():
                    worker.wait()
            event.accept()


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    if os.geteuid() != 0:
        QMessageBox.warning(None, "Info", "It is recommended to run the application with root permissions. Missing root permissions might lead to failures if certain plugins require root permissions. Watch the DEBUG outputs and retry with root privileges if the results are not satisfying.")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
