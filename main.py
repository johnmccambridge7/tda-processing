import sys
import os
import glob
import time
import numpy as np
from decimal import Decimal
from threading import Thread

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QWidget, QProgressBar,
    QCheckBox, QLineEdit, QGridLayout, QMessageBox,
    QGroupBox, QTabWidget, QSizePolicy, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from tifffile import imwrite, imread, TiffFile

from functions import process_channel
from constants import (
    WINDOW_TITLE, DEFAULT_OUTPUT_DIR, ACCEPTED_FILE_TYPES,
    COPYRIGHT_TEXT
)


class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    preview = pyqtSignal(int, QPixmap)  # Added channel index
    reference = pyqtSignal(int, QPixmap)  # Added channel index
    processed_data = pyqtSignal(int, np.ndarray)  # New signal for processed data
    save_finished = pyqtSignal(str)  # Signal when saving is done
    save_error = pyqtSignal(str)  # Signal when saving encounters an error


class ImageProcessorWorker(Thread):
    def __init__(self, file_path, reference_channel, output_dir, signals, channel_idx, scaling_params):
        super().__init__()
        self.file_path = file_path
        self.reference_channel = reference_channel
        self.output_dir = output_dir
        self.signals = signals
        self.processed_channels = {}
        self.total_channels = 1  # Each worker handles one channel
        self.total_work = self.get_total_work()
        self.progress_value = 0
        self.start_time = None
        self.channel_idx = channel_idx
        self.scaling_params = scaling_params

    def get_total_work(self):
        try:
            image_data = imread(self.file_path)
            return image_data.shape[0]  # Number of z-slices
        except:
            return 1

    def run(self):
        try:
            self.start_time = time.time()
            image_data = imread(self.file_path)
            channel_data = image_data[:, self.channel_idx, :, :]

            processed = process_channel(
                channel=channel_data,
                channel_idx=self.channel_idx,
                progress_callback=self.update_progress,
                preview_callback=lambda pixmap: self.signals.preview.emit(self.channel_idx, pixmap),
                reference_callback=lambda pixmap: self.signals.reference.emit(self.channel_idx, pixmap),
            )

            self.processed_channels[self.channel_idx] = processed

            # Emit the processed data instead of saving
            self.signals.processed_data.emit(self.channel_idx, processed)

            self.signals.finished.emit()

        except Exception as e:
            self.signals.error.emit(str(e))

    def update_progress(self, value):
        self.progress_value += value
        self.signals.progress.emit(value)


class ImageSaverWorker(Thread):
    def __init__(self, processed_channels, scaling_params, current_file, output_dir, signals):
        super().__init__()
        self.processed_channels = processed_channels
        self.scaling_params = scaling_params
        self.current_file = current_file
        self.output_dir = output_dir
        self.signals = signals

    def run(self):
        try:
            if len(self.processed_channels) != 3:
                self.signals.save_error.emit("Incomplete channel data for saving.")
                return

            # Determine ordering based on lsm510 and lsm880 flags
            ordering = list(range(len(self.processed_channels.keys())))
            if self.scaling_params.get('lsm510', 0):
                ordering[0], ordering[1] = ordering[1], ordering[0]
            elif self.scaling_params.get('lsm880', 0):
                ordering[0], ordering[2] = ordering[2], ordering[0]

            # Stack the processed channels based on the ordering
            new_image = np.array([self.processed_channels[x] for x in ordering])
            new_image = new_image.transpose((1, 0, 2, 3))

            tiff = np.array(new_image).astype(np.uint8)

            image_metadata = {
                'axes': 'ZCYX',
                'mode': 'color',
                'unit': 'um',
                'spacing': self.scaling_params.get('zstep', '1.0')
            }

            os.makedirs(self.output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            filename = f"{base_name}_PROCESSED.tiff"
            output_path = os.path.join(self.output_dir, filename)

            imwrite(
                output_path,
                tiff,
                resolution=(float(self.scaling_params.get('resolution', '1.0')), float(self.scaling_params.get('resolution', '1.0'))),
                imagej=True,
                metadata=image_metadata
            )

            # Add the saved file to the Output Directory in the file tree
            self.signals.save_finished.emit(output_path)

        except Exception as e:
            self.signals.save_error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('base-app/icon.png'))
        self.input_directories = []  # Initialize input_directories list
        self.output_directories = {}  # Dictionary to map input directories to their output directories
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #6A5ACD;
                color: white;
                border: none;
                padding: 6px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5A4ACD;
            }
            QProgressBar {
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
            QProgressBar::chunk[complete="true"] {
                background-color: #45a049;
            }
            QLabel.completed {
                color: #45a049;
                font-weight: bold;
            }
            QCheckBox {
                color: #FFFFFF;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: #FFFFFF;
                color: black;
            }
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #FFFFFF;
            }
            QTreeWidget {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background-color: #5A4ACD;
            }
            QPushButton#runButton {
                background-color: #6A5ACD;
                font-size: 12px;
                padding: 4px 16px;
            }
            QPushButton#runButton:disabled {
                background-color: #6A5ACD;
                opacity: 0.6;
            }
        """)
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.to_process = []
        self.processed_channels = {}
        self.completed_files = 0
        self.input_dir = ""
        self.selected_output_dir = ""
        self.init_ui()
        self.total_progress = 0
        self.expected_total = 0
        self.scaling_params = {
            'zstep': '1.0',
            'xscale': Decimal('1.0'),
            'yscale': Decimal('1.0'),
            'resolution': Decimal('1.00'),
            'lsm510': 0,
            'lsm880': 0
        }
        self.file_status_items = {}
        self.output_file_status_items = {}

    def init_ui(self):
        # Load custom fonts
        font_id1 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro.ttf'))
        font_families1 = QFontDatabase.applicationFontFamilies(font_id1)
        if font_families1:
            self.setFont(QFont(font_families1[0]))

        font_id2 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro-Regular.otf'))
        font_families2 = QFontDatabase.applicationFontFamilies(font_id2)
        if font_families2:
            regular_font = QFont(font_families2[0])
        else:
            regular_font = QFont("SF Pro")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()

        # Title and instructions
        title_layout = QVBoxLayout()
        title_label = QLabel("TDA Processing App")
        title_font = QFont("SF Pro", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        instructions = QLabel("Select input and output directories to start processing your images:")
        instructions_font = QFont("SF Pro", 14)
        instructions.setFont(instructions_font)
        title_layout.addWidget(instructions)

        header_layout.addLayout(title_layout)

        main_layout.addLayout(header_layout)

        # Previews & Overview
        previews_overview_group = QGroupBox("Overview")
        previews_overview_layout = QHBoxLayout()

        # Left side: Previews
        previews_layout = QHBoxLayout()
        previews_layout.setAlignment(Qt.AlignCenter)  # Center align the previews

        self.preview_labels = []
        self.reference_labels = []
        for i in range(3):
            channel_layout = QVBoxLayout()
            preview_title = QLabel(f"Channel {i + 1} Preview:")
            preview_title.setFont(QFont("SF Pro", 12))
            preview_title.setAlignment(Qt.AlignCenter)
            preview_label = QLabel()
            preview_label.setFixedSize(200, 200)
            preview_label.setStyleSheet("border: 1px solid #444444; border-radius: 5px;")
            preview_label.setAlignment(Qt.AlignCenter)
            self.preview_labels.append(preview_label)

            reference_title = QLabel(f"Channel {i + 1} Reference:")
            reference_title.setFont(QFont("SF Pro", 12))
            reference_title.setAlignment(Qt.AlignCenter)
            reference_label = QLabel()
            reference_label.setFixedSize(200, 200)
            reference_label.setStyleSheet("border: 1px solid #444444; border-radius: 5px;")
            reference_label.setAlignment(Qt.AlignCenter)
            self.reference_labels.append(reference_label)

            channel_layout.addWidget(preview_title)
            channel_layout.addWidget(preview_label)
            channel_layout.addWidget(reference_title)
            channel_layout.addWidget(reference_label)
            previews_container = QWidget()
            previews_container.setLayout(channel_layout)
            previews_layout.addWidget(previews_container)

        previews_layout.addStretch()
        previews_overview_layout.addLayout(previews_layout)

        # Create grid layout for file trees
        grid_layout = QGridLayout()

        # Add Directory button at the top
        add_directory_layout = QHBoxLayout()
        self.browse_input_button = QPushButton("Add Directory")
        self.browse_input_button.clicked.connect(self.add_input_directory)
        add_directory_layout.addWidget(self.browse_input_button)
        add_directory_layout.addStretch()
        grid_layout.addLayout(add_directory_layout, 0, 0, 1, 2)

        # File Trees Layout
        input_file_tree_group = QGroupBox("Input")
        input_file_tree_layout = QVBoxLayout()

        # Input File Tree Widget
        self.input_file_tree = QTreeWidget()
        self.input_file_tree.setHeaderLabels(["Name", "Path/Size", "Actions"])
        self.input_file_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.input_file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.input_file_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        input_file_tree_layout.addWidget(self.input_file_tree)

        input_file_tree_group.setLayout(input_file_tree_layout)
        grid_layout.addWidget(input_file_tree_group, 1, 0)

        # Output File Tree
        output_file_tree_group = QGroupBox("Output")
        output_file_tree_layout = QVBoxLayout()

        # Output File Tree Widget
        self.output_file_tree = QTreeWidget()
        self.output_file_tree.setHeaderLabels(["File Name", "Size (MB)", "Status"])
        self.output_file_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.output_file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.output_file_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        output_file_tree_layout.addWidget(self.output_file_tree)

        output_file_tree_group.setLayout(output_file_tree_layout)
        grid_layout.addWidget(output_file_tree_group, 1, 1)

        previews_overview_layout.addLayout(grid_layout)

        previews_overview_group.setLayout(previews_overview_layout)
        main_layout.addWidget(previews_overview_group)

        # Footer
        footer = QLabel(COPYRIGHT_TEXT)
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(QFont("SF Pro", 10))
        footer.setStyleSheet("color: gray;")
        main_layout.addWidget(footer)

        main_widget.setLayout(main_layout)

    def populate_input_files(self):
        self.input_file_tree.clear()
        self.file_status_items = {}
        self.processing_complete = False
        self.to_process = []

        for input_dir in self.input_directories:
            # Create directory item
            dir_name = os.path.basename(input_dir)
            dir_item = QTreeWidgetItem(self.input_file_tree)
            dir_item.setText(0, dir_name)
            dir_item.setText(1, os.path.basename(os.path.dirname(input_dir)))  # Show parent folder name
            dir_item.setToolTip(1, input_dir)  # Full path as tooltip

            # Add set output button for directory
            set_output_button = QPushButton("Set Output")
            set_output_button.setStyleSheet("font-size: 10px; padding: 2px 8px;")  # Smaller font and padding
            # Connect with lambda to pass input_dir and set_output_button
            set_output_button.clicked.connect(lambda _, d=input_dir, b=set_output_button: self.handle_output_selection(d, b))
            self.input_file_tree.setItemWidget(dir_item, 2, set_output_button)

            # Find and add files for this directory
            files = []
            for ext in ACCEPTED_FILE_TYPES:
                files.extend(glob.glob(os.path.join(input_dir, f"*{ext}")))

            if files:
                self.to_process.extend(files)
                for file_path in files:
                    file_name = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)
                    formatted_size = f"{file_size:.2f} MB"
                    file_item = QTreeWidgetItem(dir_item, [file_name, formatted_size, ""])
                    file_item.setToolTip(1, file_path)  # Full path as tooltip
                    progress_bar = QProgressBar()
                    progress_bar.setValue(0)
                    progress_bar.setMaximum(100)
                    self.input_file_tree.setItemWidget(file_item, 2, progress_bar)
                    self.file_status_items[file_path] = (file_item, progress_bar)

            dir_item.setExpanded(True)

        if not self.to_process:
            QMessageBox.warning(self, "No Files Found", "No compatible files found in the selected directories.")

    def populate_output_files(self):
        self.output_file_tree.clear()
        self.output_file_status_items = {}

        for input_dir, output_dir in self.output_directories.items():
            # Create root directory item for each output directory with dropdown
            dir_name = os.path.basename(output_dir)
            root_item = QTreeWidgetItem(self.output_file_tree, [dir_name, "", ""])
            root_item.setExpanded(False)  # Start collapsed
            # Add a small arrow icon to indicate it's expandable
            root_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

    def handle_output_selection(self, input_dir, button):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_directories.get(input_dir, self.selected_output_dir) or "")
        if selected_dir:
            self.output_directories[input_dir] = selected_dir
            button.hide()  # Hide the Set Output button after selection
            self.populate_output_files()
            
            # Get files only from the selected input directory
            files_to_process = []
            for ext in ACCEPTED_FILE_TYPES:
                files_to_process.extend(glob.glob(os.path.join(input_dir, f"*{ext}")))
                
            # Start processing only these files
            if files_to_process:
                self.to_process = files_to_process  # Override the global queue with just these files
                self.run_processing(input_dir)
            else:
                QMessageBox.warning(self, "No Files Found", "No compatible files found in the selected directory.")

    def run_processing(self, selected_input_dir=None):
        if not self.to_process:
            QMessageBox.information(self, "No Files to Process", "No files selected for processing.")
            return
            
        # When processing a specific directory, we're already working with filtered files
        files_to_process = self.to_process

        for label in self.preview_labels:
            label.clear()

        for label in self.reference_labels:
            label.clear()

        self.current_file = files_to_process[0]
        # Only remove from to_process if it's the selected directory
        if selected_input_dir:
            self.to_process.remove(self.current_file)
        else:
            self.to_process.pop(0)

        # Update the input file tree selection
        self.input_file_tree.setCurrentItem(None)

        metadata = self.extract_lsm_metadata(self.current_file)
        if metadata:
            self.scaling_params.update(metadata)

        reference_channel = self.select_reference_channel(self.current_file)
        if reference_channel is None:
            QMessageBox.warning(self, "Reference Channel Not Found", "Could not determine the reference channel for processing.")
            return

        # Initialize signals
        self.worker_signals = WorkerSignals()
        self.worker_signals.progress.connect(self.update_progress)
        self.worker_signals.finished.connect(self.worker_finished)
        self.worker_signals.error.connect(self.show_error)
        self.worker_signals.preview.connect(self.update_preview)
        self.worker_signals.reference.connect(self.update_reference)
        self.worker_signals.processed_data.connect(self.collect_processed_data)
        self.worker_signals.save_finished.connect(self.handle_save_finished)
        self.worker_signals.save_error.connect(self.show_error)

        # Initialize tracking variables
        self.processed_channels = {}
        self.workers_finished = 0
        self.expected_total = 3  # Number of channels

        # Reset progress tracking
        self.total_progress = 0

        # Determine the input directory for the current file
        input_dir = self.get_input_directory_for_file(self.current_file)
        if not input_dir:
            self.show_error("Input directory for the current file not found.")
            return

        output_dir = self.output_directories.get(input_dir, self.selected_output_dir)
        if not output_dir:
            self.show_error("Output directory not set for the input directory.")
            return

        # Start workers for each channel
        self.workers = []
        for channel_idx in range(3):
            worker = ImageProcessorWorker(
                file_path=self.current_file,
                reference_channel=reference_channel,
                output_dir=output_dir,
                signals=self.worker_signals,
                channel_idx=channel_idx,
                scaling_params=self.scaling_params
            )
            self.workers.append(worker)
            worker.start()

    def get_input_directory_for_file(self, file_path):
        for input_dir in self.input_directories:
            if os.path.commonpath([input_dir, file_path]) == input_dir:
                return input_dir
        return None

    @property
    def is_input_directory_selected(self):
        return True  # Modify based on selection logic if needed

    @property
    def is_output_directory_selected(self):
        return True  # Modify based on selection logic if needed

    def extract_lsm_metadata(self, file_path):
        try:
            with TiffFile(file_path) as tif:
                lsm_meta = tif.lsm_metadata
                if lsm_meta is None:
                    return {}
                # Parse voxel size and other metadata from lsm_meta
                voxel_size = (
                    lsm_meta.get('VoxelSizeX', '1.0'),
                    lsm_meta.get('VoxelSizeY', '1.0'),
                    lsm_meta.get('VoxelSizeZ', '1.0')
                )
                resolution = lsm_meta.get('Resolution', '1.0')
                color_channels = lsm_meta.get('Channel', [])

                scaling_params = {
                    'xscale': Decimal(voxel_size[0]),
                    'yscale': Decimal(voxel_size[1]),
                    'zstep': voxel_size[2],
                    'resolution': Decimal(resolution),
                    'lsm510': 1 if any('LSM510' in ch.get('Mode', '') for ch in color_channels) else 0,
                    'lsm880': 1 if any('LSM880' in ch.get('Mode', '') for ch in color_channels) else 0
                }
                return scaling_params
        except Exception as e:
            self.show_error(f"Error extracting metadata: {e}")
            return {}

    def select_reference_channel(self, file_path):
        image_data = imread(file_path)
        channels = image_data.shape[1]
        snr_values = []
        for channel in range(channels):
            mean = np.mean(image_data[:, channel, :, :])
            std = np.std(image_data[:, channel, :, :])
            snr = 10 * np.log10(mean / std) if std != 0 else 0
            snr_values.append(snr)
        reference_channel = np.argmax(snr_values)
        return reference_channel

    def update_progress(self, value):
        self.total_progress += value
        if self.expected_total > 0:
            total_work = self.workers[0].total_work * self.expected_total
            progress_percentage = (self.total_progress / total_work) * 100
            progress_percentage = min(progress_percentage, 100)

        # Update the input file tree progress
        if self.current_file in self.file_status_items:
            item, progress_bar = self.file_status_items[self.current_file]
            progress_bar.setValue(int(progress_percentage))
            if progress_percentage >= 100:
                progress_bar.setProperty("complete", True)
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #45a049; }")
                completed_label = QLabel("Done")
                completed_label.setStyleSheet("color: #45a049;")
                self.input_file_tree.setItemWidget(item, 2, completed_label)

    def update_preview(self, channel_idx, pixmap):
        if 0 <= channel_idx < len(self.preview_labels):
            self.preview_labels[channel_idx].setPixmap(pixmap)

    def update_reference(self, channel_idx, pixmap):
        if 0 <= channel_idx < len(self.reference_labels):
            self.reference_labels[channel_idx].setPixmap(pixmap)

    def collect_processed_data(self, channel_idx, data):
        self.processed_channels[channel_idx] = data

    def worker_finished(self):
        self.workers_finished += 1
        if self.workers_finished == self.expected_total:
            # Determine the input directory for the current file
            input_dir = self.get_input_directory_for_file(self.current_file)
            if not input_dir:
                self.show_error("Input directory for the current file not found.")
                return

            output_dir = self.output_directories.get(input_dir, self.selected_output_dir)
            if not output_dir:
                self.show_error("Output directory not set for the input directory.")
                return

            # Start the saving process in a separate thread
            saver_worker = ImageSaverWorker(
                processed_channels=self.processed_channels,
                scaling_params=self.scaling_params,
                current_file=self.current_file,
                output_dir=output_dir,
                signals=self.worker_signals
            )
            saver_worker.start()
            self.completed_files += 1
            if self.to_process:
                self.run_processing()
            else:
                QMessageBox.information(self, "Processing Complete", "All files have been processed!")
                # Mark processing as complete
                self.processing_complete = True

    def save_combined_image(self):
        # This method is no longer called directly from worker_finished
        pass

    def handle_save_finished(self, output_path):
        # Find the root item for the corresponding output directory
        output_dir = self.output_dir
        for input_dir, out_dir in self.output_directories.items():
            if out_dir == os.path.dirname(output_path):
                output_dir = out_dir
                break

        # Find the root item for this output directory
        root = None
        for i in range(self.output_file_tree.topLevelItemCount()):
            item = self.output_file_tree.topLevelItem(i)
            if item.text(0) == os.path.basename(output_dir):
                root = item
                break

        if root:
            # Add the saved file under the root directory
            file_name = os.path.basename(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
            formatted_size = f"{file_size:.2f} MB"
            item = QTreeWidgetItem(root, [file_name, formatted_size, "Saved"])
            self.output_file_status_items[output_path] = (item, None)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def add_input_directory(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if selected_dir and selected_dir not in self.input_directories:
            self.input_directories.append(selected_dir)

            # Refresh the input files display
            self.populate_input_files()

    def remove_input_directory(self, directory, item):
        if directory in self.input_directories:
            self.input_directories.remove(directory)
            root = self.directory_list.invisibleRootItem()
            root.removeChild(item)
            self.populate_input_files()

    def set_output_directory(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.selected_output_dir or "")
        if selected_dir:
            self.selected_output_dir = selected_dir
            self.output_dir_line_edit.setText(selected_dir)
            self.populate_output_files()


def main():
    app = QApplication(sys.argv)

    # Load custom fonts before creating the main window
    font_id1 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro.ttf'))
    font_families1 = QFontDatabase.applicationFontFamilies(font_id1)
    if font_families1:
        app.setFont(QFont(font_families1[0]))

    font_id2 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro-Regular.otf'))
    font_families2 = QFontDatabase.applicationFontFamilies(font_id2)
    if font_families2:
        regular_font = QFont(font_families2[0])
    else:
        regular_font = QFont("SF Pro")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
