import sys
import os
import glob
import time
import numpy as np
from threading import Thread

from scipy.ndimage import gaussian_filter

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QWidget, QProgressBar,
    QGridLayout, QMessageBox,
    QGroupBox, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QTreeWidgetItemIterator
)
from snake_game import SnakeGame
from PyQt5.QtGui import QPixmap, QIcon, QFont, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer

### for czi images
from lxml import etree
import czifile as czi

### for lsm
from tifffile import imwrite, imread, TiffFile

from functions import process_channel
from constants import (
    WINDOW_TITLE, DEFAULT_OUTPUT_DIR, ACCEPTED_FILE_TYPES,
    COPYRIGHT_TEXT
)
from lsm_types import LSMMetadata

def czi_imread(filename):
    with czi.CziFile(filename) as image:
        metadata = image.metadata()  # Extract metadata as XML
        pixels = image.asarray()
        channels = pixels[0, 0, 0, :, :, :, :].squeeze()  # Selecting the channels only
        channels = np.transpose(channels, (1,0,2,3)) #transposing so we have Z, C, X, Y
        return channels

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

        print(f"IPW: Setting scaling params for: {self.file_path} with {scaling_params.keys()}")

        self.scaling_params = scaling_params
        self.is_czi_file = ".czi" in file_path

    def get_total_work(self):
        try:
            image_data = imread(self.file_path) if not self.is_czi_file else czi_imread(self.file_path)
            return image_data.shape[0]  # Number of z-slices
        except:
            return 1

    def run(self):
        try:
            self.start_time = time.time()
            image_data = imread(self.file_path) if not self.is_czi_file else czi_imread(self.file_path)
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
        print(f"ISM: Setting scaling params for: {current_file} with {scaling_params.keys()}")

        self.scaling_params = scaling_params
        self.current_file = current_file
        self.output_dir = output_dir
        self.signals = signals
        self.daemon = True  # Make thread daemon so it exits when main program does

    def run(self):
        try:
            output_path = self._save_image()
            if output_path:
                self.signals.save_finished.emit(output_path)
        except Exception as e:
            self.signals.save_error.emit(str(e))

    def _save_image(self):
        # Get channel order from scaling params
        #
        # todo: find channel information for czi images
        #

        print(f"Obtained channel order: {self.scaling_params.get('channel_order', [])}")

        channel_order = self.scaling_params.get('channel_order', [1, 0])
        if not channel_order:
            channel_order = list(range(len(self.processed_channels)))

        if len(channel_order) < 2:
            raise ValueError("Insufficient channels to create an RGB image.")
        
        print(print(self.scaling_params.keys()), channel_order, len(self.processed_channels))
        if len(self.processed_channels) != len(set(channel_order)):
            raise ValueError(f"Channel count mismatch: Expected {len(set(channel_order))} channels but got {len(self.processed_channels)}.")

        # Create RGB image
        ordered_processed = [self.processed_channels[idx] for idx in range(len(self.processed_channels))]

        rgb_image = np.stack(
            [ordered_processed[channel_order[i]] if i < len(channel_order) else np.zeros_like(ordered_processed[0])
             for i in range(len(self.processed_channels))], axis=0
        )
        rgb_image = rgb_image.transpose((1, 0, 2, 3))
        tiff = rgb_image.astype(np.uint8)

        # Prepare output path
        os.makedirs(self.output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        filename = f"{base_name}_PROCESSED.tiff"
        output_path = os.path.join(self.output_dir, filename)

        imwrite(
            output_path,
            tiff,
            resolution=(float(self.scaling_params.get('resolution', '1.0')),
                        float(self.scaling_params.get('resolution', '1.0'))),
            imagej=True,
            metadata={
                'axes': 'ZCYX',
                'mode': 'color',
                'unit': 'um',
                'spacing': self.scaling_params['z-step'],
            }
        )

        return output_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.games_expanded = False
        # Get screen dimensions and set window to full size
        screen = QApplication.primaryScreen().size()
        self.resize(screen.width(), screen.height())
        self.setWindowIcon(QIcon('base-app/icon.png'))
        self.input_directories = []  # Initialize input_directories list
        self.output_directories = {}  # Dictionary to map input directories to their output directories
        self.directories_with_output = set()  # Track which directories have output set
        self.file_progress = {}  # Dictionary to store progress for each file
        self.output_files = {}  # Dictionary to store output files for each directory
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
            QHeaderView::section {
                background-color: #4A4A4A;
                color: white;
                padding: 4px 8px;
                border: none;
                border-right: 1px solid #555555;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #555555;
            }
            QHeaderView::section:checked {
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
            'VoxelSizeX': 1.0,
            'VoxelSizeY': 1.0,
            'VoxelSizeZ': 1.0,
            'resolution': 1.0,
            'lsm510': 0,
            'lsm880': 0,
            'channel_order': [],
            'z-step': 0,
            'source': {},
        }
        self.file_status_items = {}
        self.output_file_status_items = {}

    def init_ui(self):
        # Load custom fonts
        font_id1 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro.ttf'))
        font_families1 = QFontDatabase.applicationFontFamilies(font_id1)
        if font_families1:
            self.setFont(QFont(font_families1[0]))

        font_id2 = QFontDatabase.addApplicationFont(
            os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro-Regular.otf'))
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
        header_layout.addLayout(title_layout)
        
        # Add stretch to push arcade button to the right
        header_layout.addStretch()
        
        # Hidden arcade button
        self.arcade_btn = QPushButton("🎮")
        self.arcade_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #555555;
                max-width: 30px;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #4CAF50;
            }
        """)
        self.arcade_btn.setToolTip("Secret Arcade Mode")
        self.arcade_btn.clicked.connect(self.toggle_arcade)
        header_layout.addWidget(self.arcade_btn)
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
        # Preview labels will be created dynamically when processing starts
        self.previews_layout = previews_layout  # Store for later use

        previews_overview_layout.addLayout(previews_layout)

        # Create grid layout for file trees with equal column widths
        grid_layout = QGridLayout()
        grid_layout.setColumnStretch(0, 1)  # Input tree gets 1 part
        grid_layout.setColumnStretch(1, 1)  # Output tree gets 1 part

        # File Trees Layout
        input_file_tree_group = QGroupBox("Input")
        input_file_tree_layout = QVBoxLayout()

        # Input File Tree Widget
        self.input_file_tree = QTreeWidget()
        self.input_file_tree.setHeaderLabels(["Name", "Path/Size", ""])
        self.input_file_tree.itemSelectionChanged.connect(self.handle_input_selection)

        # Add Directory button as first row
        add_dir_item = QTreeWidgetItem(self.input_file_tree)
        add_dir_item.setText(0, "+ Add Folder")
        add_dir_item.setText(1, "Click to add a new directory")
        add_dir_item.setToolTip(0, "Click to add a new input directory")

        # Style the "Add Directory" row
        font = add_dir_item.font(0)
        font.setBold(True)
        add_dir_item.setFont(0, font)

        # Connect item click to add_input_directory
        self.input_file_tree.itemClicked.connect(
            lambda item: self.add_input_directory() if item == add_dir_item else None
        )
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
        saved_progress = self.file_progress.copy()  # Save current progress

        for input_dir in self.input_directories:
            # Create directory item
            dir_name = os.path.basename(input_dir)
            dir_item = QTreeWidgetItem(self.input_file_tree)
            dir_item.setText(0, dir_name)
            dir_item.setText(1, os.path.basename(os.path.dirname(input_dir)))  # Show parent folder name
            dir_item.setToolTip(1, input_dir)  # Full path as tooltip

            # Only show Set Output button if directory doesn't have output set
            if input_dir not in self.directories_with_output:
                set_output_button = QPushButton("Set Output Folder")
                set_output_button.setStyleSheet("""
                    font-size: 10px; 
                    padding: 2px 8px;
                    background-color: #ecf0f1;
                    color: black;
                """)  # Warning colors with smaller font and padding
                set_output_button.clicked.connect(lambda _, d=input_dir: self.handle_output_selection(d))
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
                    try:
                        if file_path in saved_progress and saved_progress[file_path] >= 100:
                            completed_label = QLabel("Done")
                            completed_label.setStyleSheet("color: #45a049;")
                            self.input_file_tree.setItemWidget(file_item, 2, completed_label)
                        else:
                            progress_bar = QProgressBar()
                            progress_bar.setValue(saved_progress.get(file_path, 0))
                            progress_bar.setMaximum(100)
                            self.input_file_tree.setItemWidget(file_item, 2, progress_bar)
                        self.file_status_items[file_path] = (file_item, progress_bar if file_path not in saved_progress or
                                                                                        saved_progress[
                                                                                            file_path] < 100 else None)
                    except Exception as e:
                        print(f"oh buggor: {e}")
            dir_item.setExpanded(True)

        if not self.to_process:
            QMessageBox.warning(self, "No Files Found", "No compatible files found in the selected directories.")

        # Add Directory button as first row
        add_dir_item = QTreeWidgetItem(self.input_file_tree)
        add_dir_item.setText(0, "+ Add Folder")
        add_dir_item.setText(1, "Click to add a new directory")  # Add descriptive text
        add_dir_item.setToolTip(0, "Click to add a new input directory")
        add_dir_item.is_add_directory = True  # Custom attribute to identify this item

        # Style the "Add Directory" row
        font = add_dir_item.font(0)
        font.setBold(True)
        add_dir_item.setFont(0, font)
        add_dir_item.setFont(1, font)  # Also bold the description

        # Ensure the click handler is properly connected
        self.input_file_tree.itemClicked.disconnect()
        self.input_file_tree.itemClicked.connect(
            lambda item: self.add_input_directory() if getattr(item, 'is_add_directory', False) else None
        )

    def populate_output_files(self):
        self.output_file_tree.clear()
        self.output_file_status_items = {}

        for input_dir, output_dir in self.output_directories.items():
            # Create root directory item for each output directory with dropdown
            dir_name = os.path.basename(output_dir)
            root_item = QTreeWidgetItem(self.output_file_tree, [dir_name, "", ""])
            root_item.setExpanded(True)  # Start expanded
            root_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

            # Restore any saved output files for this directory
            if output_dir in self.output_files:
                for output_path in self.output_files[output_dir]:
                    if os.path.exists(output_path):  # Verify file still exists
                        file_name = os.path.basename(output_path)
                        file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
                        formatted_size = f"{file_size:.2f} MB"
                        item = QTreeWidgetItem(root_item, [file_name, formatted_size, "Saved"])
                        self.output_file_tree.setItemWidget(item, 2, QLabel(""))
                        self.output_file_status_items[output_path] = (item, None)

    def handle_output_selection(self, input_dir):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory",
                                                        self.output_directories.get(input_dir,
                                                                                    self.selected_output_dir) or "")
        if selected_dir:
            self.output_directories[input_dir] = selected_dir
            self.directories_with_output.add(input_dir)  # Mark this directory as having output set
            self.populate_input_files()  # Refresh the display
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

    def create_preview_labels(self, num_channels):
        # Clear existing preview layout
        while self.previews_layout.count():
            item = self.previews_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.preview_labels = []
        self.reference_labels = []
        
        for i in range(num_channels):
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
            self.previews_layout.addWidget(previews_container)

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
            self.scaling_params = metadata

        reference_channel = self.select_reference_slice(self.current_file)
        if reference_channel is None:
            QMessageBox.warning(self, "Reference Channel Not Found",
                                "Could not determine the reference channel for processing.")
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
        # expected_total will be set when starting workers based on actual channels

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

        is_czi_file = ".czi" in self.current_file

        # Get number of channels from the image
        image_data = imread(self.current_file) if not is_czi_file else czi_imread(self.current_file)
        num_channels = image_data.shape[1]
        print(self.current_file, num_channels, is_czi_file)
        self.expected_total = num_channels  # Update expected total
        
        # Create preview labels for the actual number of channels
        self.create_preview_labels(num_channels)

        # Start workers for each channel
        self.workers = []
        for channel_idx in range(num_channels):
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
            is_czi_file = ".czi" in file_path

            if is_czi_file:
                with czi.CziFile(file_path) as image:
                    raw_xml = image.metadata()  # Get the full XML metadata string
                    root = etree.fromstring(raw_xml)
                    scaling_values = {}
                    scaling_items = root.xpath(".//Scaling/Items")

                    if scaling_items:
                        for distance in scaling_items[0].xpath("Distance"):  # Iterate over <Distance> elements
                            axis = distance.attrib.get("Id")  # Extract X, Y, or Z from the attribute
                            value_elem = distance.find("Value")  # Find the <Value> tag
                            if axis and value_elem is not None:
                                try:
                                    # Convert the value from meters to micrometers
                                    value_in_microns = float(value_elem.text) * 1e6  
                                    scaling_values[f"VoxelSize{axis}"] = value_in_microns
                                except ValueError:
                                    print(f"Warning: Could not convert value for axis {axis}")

                    # If available, set the z-step (or default to 1.0)
                    scaling_values["z-step"] = scaling_values.get("VoxelSizeZ", 1.0)

                    # Compute resolution if both X and Y voxel sizes are available.
                    if "VoxelSizeX" in scaling_values and "VoxelSizeY" in scaling_values:
                        resolution_x = 1.0 / scaling_values["VoxelSizeX"] if scaling_values["VoxelSizeX"] > 0 else 0
                        resolution_y = 1.0 / scaling_values["VoxelSizeY"] if scaling_values["VoxelSizeY"] > 0 else 0
                        scaling_values["resolution"] = (resolution_x + resolution_y) / 2
                    else:
                        scaling_values["resolution"] = 1.0

                    # Store the full raw XML metadata so it can be passed along later if needed.
                    scaling_values["czi_metadata"] = raw_xml
                    return scaling_values

            # (The non-CZI branch remains unchanged)
            if not is_czi_file:
                with TiffFile(file_path) as tif:
                    if not tif.lsm_metadata:
                        return {}

                    metadata = LSMMetadata(**tif.lsm_metadata)
                    voxel_size_x = float(metadata.VoxelSizeX) * 1e6
                    voxel_size_y = float(metadata.VoxelSizeY) * 1e6
                    voxel_size_z = float(metadata.VoxelSizeZ) * 1e6

                    resolution_x = 1.0 / voxel_size_x if voxel_size_x > 0 else 0
                    resolution_y = 1.0 / voxel_size_y if voxel_size_y > 0 else 0
                    resolution = (resolution_x + resolution_y) / 2

                    channel_order = []
                    if metadata.ChannelColors and metadata.ChannelColors.Colors:
                        color_map = {
                            (0, 255, 0): 1,  # Green -> 1
                            (255, 0, 0): 0,  # Red -> 0
                            (0, 0, 255): 2   # Blue -> 2
                        }
                        for color in metadata.ChannelColors.Colors:
                            rgb = tuple(color[:3])
                            if rgb in color_map:
                                channel_order.append(color_map[rgb])
                    if not channel_order:
                        channel_order = list(range(metadata.DimensionChannels))

                    is_lsm510 = 0
                    is_lsm880 = 0
                    if metadata.ScanInformation and metadata.ScanInformation.Tracks:
                        for track in metadata.ScanInformation.Tracks:
                            if track.Name.lower().startswith('lsm510'):
                                is_lsm510 = 1
                            elif track.Name.lower().startswith('lsm880'):
                                is_lsm880 = 1

                    scaling_params = {
                        'VoxelSizeX': voxel_size_x,
                        'VoxelSizeY': voxel_size_y,
                        'VoxelSizeZ': voxel_size_z,
                        'resolution': resolution,
                        'lsm510': is_lsm510,
                        'lsm880': is_lsm880,
                        'channel_order': channel_order,
                        'z-step': voxel_size_z,
                        'source': metadata
                    }
                    return scaling_params

        except Exception as e:
            self.show_error(f"Error extracting metadata: {e}")
            return {}

    def select_reference_slice(self, file_path, channel=None, sigma=1):
        """
        Selects the best reference slice (2D image) from a 3D stack in a given channel.
        The best slice is defined as the one with the highest SNR after denoising.

        Parameters:
        file_path (str): The path to the image file.
        channel (int, optional): Which channel to use for selection. If None, defaults to 0.
        sigma (float): The sigma value for the Gaussian filter used in denoising.

        Returns:
        best_slice_index (int): The index of the best (reference) slice.
        best_denoised_slice (ndarray): The denoised image (2D array) of the best slice.
        best_snr (float): The SNR of the best slice.
        """
        # Load image data using the appropriate reader (assumes shape: [Z, C, X, Y])
        if ".czi" in file_path:
            image_data = czi_imread(file_path)
        else:
            image_data = imread(file_path)
        
        # Ensure we have the expected shape
        if image_data.ndim != 4:
            raise ValueError("Expected image data of shape [Z, C, X, Y].")
        
        num_slices, num_channels, _, _ = image_data.shape
        
        # If no channel is specified, default to channel 0
        if channel is None:
            channel = 0
        if channel >= num_channels:
            raise ValueError(f"Requested channel {channel} exceeds the number of channels ({num_channels}).")
        
        best_snr = -np.inf
        best_slice_index = None
        best_denoised_slice = None

        # Iterate over each slice (z-slice) for the given channel
        for z in range(num_slices):
            slice_data = image_data[z, channel, :, :].astype(np.float64)
            
            # Denoise the slice using a Gaussian filter
            denoised = gaussian_filter(slice_data, sigma=sigma)
            
            # Compute background: use the 5th percentile of pixel values
            background = np.percentile(denoised, 20)
            # Compute a robust noise estimate using the median absolute deviation (MAD)
            median_val = np.median(denoised)
            mad = np.median(np.abs(denoised - median_val))
            noise = mad * 1.4826  # Convert MAD to approximate standard deviation
            if noise < 1e-6:
                noise = 1e-6
            
            # Define signal as the mean of pixels above the background.
            above_bg = denoised[denoised > background]
            signal = np.mean(above_bg) if above_bg.size > 0 else np.mean(denoised)
            
            # Calculate SNR for this slice.
            snr = (signal - background) / noise
            
            # For debugging, you can print per-slice SNR:
            print(f" - Slice {z}: signal={signal:.2f}, background={background:.2f}, noise={noise:.2f}, SNR={snr:.2f}")
            
            # Update best slice if this slice has a higher SNR.
            if snr > best_snr:
                best_snr = snr
                best_slice_index = z
                best_denoised_slice = denoised

        print(f"*** Picked: {best_slice_index} with {best_snr}")

        return best_denoised_slice

    def update_progress(self, value):
        self.total_progress += value
        if self.expected_total > 0:
            total_work = self.workers[0].total_work * self.expected_total
            progress_percentage = (self.total_progress / total_work) * 100
            progress_percentage = min(progress_percentage, 100)
        
        # Store progress
        self.file_progress[self.current_file] = progress_percentage
        
        if self.current_file in self.file_status_items:
            item, progress_bar = self.file_status_items[self.current_file]
            if progress_bar is not None:
                try:
                    progress_bar.setValue(int(progress_percentage))
                    if progress_percentage >= 100:
                        progress_bar.setProperty("complete", True)
                        progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #45a049; }")
                        completed_label = QLabel("Done")
                        completed_label.setStyleSheet("color: #45a049;")
                        self.input_file_tree.setItemWidget(item, 2, completed_label)
                        # Remove the reference to the progress bar since it has been replaced
                        self.file_status_items[self.current_file] = (item, None)
                except Exception as e:
                    print(f"fuk: {e}")


    def update_preview(self, channel_idx, pixmap):
        if 0 <= channel_idx < len(self.preview_labels):
            self.preview_labels[channel_idx].setPixmap(pixmap)

    def update_reference(self, channel_idx, pixmap):
        if 0 <= channel_idx < len(self.reference_labels):
            self.reference_labels[channel_idx].setPixmap(pixmap)

    def collect_processed_data(self, channel_idx, data):
        """Collect processed channel data"""
        self.processed_channels[channel_idx] = data

    def update_combo(self):
        current_time = time.time()
        if current_time - self.last_collect_time < 1.5:  # 1.5 seconds window for combo
            self.combo_multiplier = min(self.combo_multiplier + 1, 10)  # Max 10x multiplier
            self.combo_timer = 100  # Reset combo timer
        else:
            self.combo_multiplier = 1
        self.last_collect_time = current_time
        self.max_combo = max(self.max_combo, self.combo_multiplier)

    def worker_finished(self):
        """Handle completion of a channel processing worker"""
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

    def save_combined_image(self, output_path):
        """Update UI after save is complete"""
        try:
            output_dir = os.path.dirname(output_path)
            
            # Update data structures
            if output_dir not in self.output_files:
                self.output_files[output_dir] = []
            self.output_files[output_dir].append(output_path)

            # Find or create root item
            root = self._get_or_create_output_root(output_dir)
            
            # Create file item
            file_name = os.path.basename(output_path)
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            item = QTreeWidgetItem(root, [
                file_name,
                f"{file_size:.2f} MB",
                ""
            ])
            
            # Add status label
            status_label = QLabel("Saved")
            status_label.setStyleSheet("color: #45a049;")
            self.output_file_tree.setItemWidget(item, 2, status_label)
            self.output_file_status_items[output_path] = (item, None)
            
        except Exception as e:
            self.show_error(f"Error updating UI after save: {e}")

    def _get_or_create_output_root(self, output_dir):
        """Get or create root item for output directory"""
        dir_name = os.path.basename(output_dir)
        for i in range(self.output_file_tree.topLevelItemCount()):
            item = self.output_file_tree.topLevelItem(i)
            if item.text(0) == dir_name:
                return item
                
        # Create new root if not found
        root = QTreeWidgetItem(self.output_file_tree, [dir_name])
        root.setExpanded(True)
        return root

    def handle_input_selection(self):
        selected_items = self.input_file_tree.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]
        if getattr(selected_item, 'is_add_directory', False):
            return

        # Get the full path from the tooltip
        input_path = selected_item.toolTip(1)
        if not input_path:
            return

        # Find corresponding output file
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        processed_name = f"{base_name}_PROCESSED.tiff"

        # Search through output tree and select matching item
        self.output_file_tree.clearSelection()
        iterator = QTreeWidgetItemIterator(self.output_file_tree)
        while iterator.value():
            item = iterator.value()
            if item.text(0) == processed_name:
                item.setSelected(True)
                self.output_file_tree.scrollToItem(item)
                break
            iterator += 1

    def handle_save_finished(self, output_path):
        """Handle save completion signal from worker thread"""
        try:
            # Update UI in a lightweight way
            self.save_combined_image(output_path)
            
            # Schedule next file processing if needed
            if self.to_process:
                # Use a short timer to allow UI to update
                QTimer.singleShot(100, lambda: self.run_processing())
            else:
                self.processing_complete = True
                # Show completion message in a non-blocking way
                QTimer.singleShot(200, lambda: QMessageBox.information(
                    self, "Processing Complete", "All files have been processed!"))
                
        except Exception as e:
            self.show_error(f"Error handling save completion: {e}")

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

    def create_arcade_window(self):
        """Create the arcade window"""
        self.arcade_window = QMainWindow()
        self.arcade_window.setWindowTitle("Processing Arcade")
        self.arcade_window.setStyleSheet("background-color: #2E2E2E;")
        
        central_widget = QWidget()
        self.arcade_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Games grid layout (2x2)
        games_grid = QGridLayout()
        
        # Create single snake game instance
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        title_label = QLabel("Snake (Arrow keys)")
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title_label)
        
        self.snakegame = SnakeGame()
        container_layout.addWidget(self.snakegame)
        
        games_grid.addWidget(container, 0, 0)
        
        layout.addLayout(games_grid)
        
        game_instructions = QLabel("Play while processing!\nR to restart either game")
        game_instructions.setStyleSheet("color: white;")
        game_instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(game_instructions)
        
        # Set a reasonable size for the arcade window
        self.arcade_window.resize(800, 800)

    def toggle_arcade(self):
        """Toggle the arcade window visibility"""
        if not hasattr(self, 'arcade_window'):
            self.create_arcade_window()
        
        if self.arcade_window.isVisible():
            self.arcade_window.hide()
            self.arcade_btn.setText("🎮")
        else:
            self.arcade_window.show()
            self.arcade_btn.setText("🎮")


def main():
    app = QApplication(sys.argv)

    # Load custom fonts before creating the main window
    font_id1 = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), 'fonts', 'SF-Pro.ttf'))
    font_families1 = QFontDatabase.applicationFontFamilies(font_id1)
    if font_families1:
        app.setFont(QFont(font_families1[0]))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
