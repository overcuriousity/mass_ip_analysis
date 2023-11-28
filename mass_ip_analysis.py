import csv
import re
import requests
import importlib
import glob
import os
import logging
import sys
import yaml
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QCheckBox, QLineEdit, QStatusBar, QComboBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def import_required_packages():
    required_packages = [
        'PyQt5', 'requests', 'yaml', 're'
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

def load_plugins(plugin_folder='plugins'):
    plugins = {}
    plugin_dir = os.path.join(os.path.dirname(__file__), plugin_folder)

    for py_file in glob.glob(os.path.join(plugin_dir, '*.py')):
        plugin_base_name = os.path.basename(py_file)[:-3]
        plugin_path = os.path.relpath(py_file, os.path.dirname(__file__))
        plugin_name = plugin_path.replace(os.sep, '.')[:-3]
        plugins[plugin_base_name] = {'type': 'python', 'name': plugin_name}

    return plugins

def execute_plugin(plugin, entity, command_flag=None):
    try:
        if plugin['type'] == 'python':
            plugin_module = importlib.import_module(plugin['name'])
            result = plugin_module.run(entity, command_flag)
            if isinstance(result, dict) and 'success' in result and 'result' in result:
                return result
            else:
                raise ValueError("Plugin returned data in an unexpected format")
    except Exception as e:
        logging.error(f"Error executing plugin {plugin['name']} for entity {entity}: {e}")
        return {'success': False, 'result': str(e)}


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
    update_table_signal = pyqtSignal(list, int)  # list of data and row number
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # Signal for reporting errors
    def __init__(self, input_file, plugins, output_file, command_flags, parser_config):
        super().__init__()
        self.input_file = input_file
        self.plugins = plugins
        self.output_file = output_file
        self.command_flags = command_flags
        self.parser_regex = parser_config['regex']
        self.parser_entity_type = parser_config['entity_type']
    
    def run(self):
        try:
            with open(self.input_file, newline='') as infile, open(self.output_file, 'w', newline='') as outfile:
                reader = csv.reader(infile)
                writer = csv.writer(outfile)
                self.process_csv(reader, writer)
                self.finished.emit()
                logging.debug(f"finished processing csv")
        except Exception as e:
            logging.error(f"Error in CsvWorker: {e}")
            self.error_occurred.emit(str(e))

    def process_csv(self, reader, writer):
        headers = next(reader, None)  # Read the header row if it exists
        self.update_headers(headers, writer)

        for current_line, row in enumerate(reader, start=1 if headers else 0):
            logging.debug(f"Processing line {current_line}: {row}")
            new_row = self.process_row(row, current_line)
            self.update_table_signal.emit(new_row, current_line - 1)
            writer.writerow(new_row)

    def update_headers(self, headers, writer):
        if headers:
            for plugin_name in self.plugins.keys():
                headers.append(f"{self.parser_entity_type}_{plugin_name}")
            writer.writerow(headers)

    def process_row(self, row, current_line):
        new_row = row.copy()
        for cell_index, cell in enumerate(row):
            matches = re.findall(self.parser_regex, cell)
            for match in matches:
                new_row.extend(self.process_entity(match, current_line, cell_index))
        return new_row

    def process_entity(self, entity, current_line, cell_index):
        results = []
        for plugin_name, plugin in self.plugins.items():
            self.update_status.emit(plugin_name, entity, current_line, cell_index)
            plugin_result = execute_plugin(plugin, entity, self.command_flags.get(plugin_name, ""))
            if isinstance(plugin_result, dict) and 'success' in plugin_result and 'result' in plugin_result:
                if plugin_result['success']:
                    results.append(plugin_result['result'])
                else:
                    self.error_occurred.emit(plugin_result['result'])
            else:
                self.error_occurred.emit("Plugin result format is incorrect")
        return results

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mass IP Analysis')
        self.setMinimumSize(500, 400)  # Allow the window to be resized

        self.selected_output_file = None
        self.parsers = self.load_parsers('parser')
        self.plugins = load_plugins('plugins')  # Load plugins from the 'plugins' folder

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        parser_label = QLabel("Select which entities to inspect:")
        main_layout.addWidget(parser_label)
        
        self.create_parser_selector(main_layout)

        # Plugin layouts
        self.checkboxes = {}
        self.command_flags = {}
        for plugin_name in self.plugins.keys():
            checkbox = QCheckBox()
            command_flag_input = QLineEdit()
            self.checkboxes[plugin_name] = checkbox
            self.command_flags[plugin_name] = command_flag_input
            plugin_label = QLabel(f"<a href='{plugin_name}'>{plugin_name}</a>")
            plugin_label.setOpenExternalLinks(False)
            plugin_label.linkActivated.connect(self.on_plugin_link_clicked)
            plugin_layout = QHBoxLayout()
            plugin_layout.addWidget(checkbox)
            plugin_layout.addWidget(plugin_label)  # Add the label to the layout
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
        self.error_label.setText("Operation is nominal. Only use tools you are legally allowed to.")

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

        # Table setup
        self.table_widget = QTableWidget()
        main_layout.addWidget(self.table_widget)

    def load_parsers(self, parser_folder):
        parsers = {}
        parser_dir = os.path.join(os.path.dirname(__file__), parser_folder)
        for yaml_file in glob.glob(os.path.join(parser_dir, '*.yaml')):
            with open(yaml_file, 'r') as file:
                parser_config = yaml.safe_load(file)
                parsers[os.path.basename(yaml_file).split('.')[0]] = parser_config
        return parsers   

    def create_parser_selector(self, layout):
        self.parser_selector = QComboBox()
        self.parser_selector.addItems(self.parsers.keys())
        layout.addWidget(self.parser_selector)     
    
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
        selected_parser = self.parsers[self.parser_selector.currentText()]
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

        for file_path in self.file_paths:
            worker = CsvWorker(file_path, selected_plugins, self.selected_output_file, command_flags, selected_parser)
            worker.update_status.connect(self.update_status_message)
            worker.update_table_signal.connect(self.update_table)
            worker.error_occurred.connect(self.handle_plugin_error)
            worker.finished.connect(self.on_worker_finished)  # Connect finished signal
            worker.start()
            self.worker_threads.append(worker)


    def update_status_message(self, plugin_name, entity, current_line, cell_index):
        status_message = f"Processing {plugin_name} on {entity} (Line {current_line}, Cell {cell_index})"
        self.status_label.setText(status_message)

    @pyqtSlot(str)
    def on_plugin_link_clicked(self, link):
        self.display_plugin_description(link)

    @pyqtSlot()
    def on_worker_finished(self):
        # Safely remove and delete finished workers
        for worker in self.worker_threads[:]:
            if not worker.isRunning():
                self.worker_threads.remove(worker)
                worker.deleteLater()

        if not self.worker_threads:
            self.status_label.setText("Analysis completed!")

    def display_plugin_description(self, plugin_name):
        # Ensure the plugin name is not empty and correctly formatted
        if not plugin_name:
            QMessageBox.warning(self, "Error", "Invalid plugin name.")
            return

        yaml_file_path = os.path.join(os.path.dirname(__file__), f'plugins/{plugin_name}.yaml')
        try:
            with open(yaml_file_path, 'r') as file:
                plugin_config = yaml.safe_load(file)
                description = plugin_config.get('description', 'No description available.')
                QMessageBox.information(self, f"{plugin_name} Description", description)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load description for {plugin_name}: {e}")
    
    def handle_finished_worker(self):
        worker = self.sender()
        if worker:
            worker.deleteLater()  # Safely delete the worker
        # Refresh the worker_threads list to only keep running threads
        self.worker_threads = [thread for thread in self.worker_threads if thread.isRunning()]
        # Now check if all threads have finished
        if not self.worker_threads:
            self.status_label.setText("Analysis completed!")  # Update the status label

    def update_table(self, row_data, row_number):
        current_row_count = self.table_widget.rowCount()
        if row_number >= current_row_count:
            self.table_widget.insertRow(row_number)

        for col_number, cell_data in enumerate(row_data):
            if col_number >= self.table_widget.columnCount():
                self.table_widget.insertColumn(col_number)
            item = QTableWidgetItem(cell_data)
            self.table_widget.setItem(row_number, col_number, item)
    
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
