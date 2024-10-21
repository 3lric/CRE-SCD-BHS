import sys
import os
import json
import csv
import webbrowser
import logging
import shutil  # Added for file operations
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QFileDialog,
    QHeaderView, QComboBox, QPushButton, QLabel, QStyle, QAction, QToolTip, QStyledItemDelegate, QLineEdit, QMenu,
    QMessageBox, QAbstractItemView, QInputDialog, QCompleter, QDialog, QScrollArea, QAbstractScrollArea
)
from PyQt5.QtCore import Qt, QEvent, QSettings, QModelIndex
from PyQt5.QtGui import QFont, QIcon, QBrush, QColor, QClipboard, QPainter, QFontMetrics, QStandardItemModel, QStandardItem, QKeySequence, QPalette, QFontDatabase

from theme_manager import load_themes, dict_to_stylesheet
from menu_helpers import create_menu
from opcode_editor import open_opcode_editor
from table_helpers import move_row_up, move_row_down

# Set up logging
logging.basicConfig(level=logging.INFO)

def get_app_path(subdirectory=""):
    """Get the application path, accounting for PyInstaller's temporary directory."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    if subdirectory:
        return os.path.join(base_path, subdirectory)
    return base_path

def ensure_writable_json_files():
    """Ensure that JSON files are copied to a writable directory if running as a bundled executable."""
    json_dir = get_app_path("json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    # List of JSON files
    json_files = ["re1_opcodes.json", "re15_opcodes.json", "re2_opcodes.json", "re3_opcodes.json", "themes.json"]
    for file_name in json_files:
        dest_file = os.path.join(json_dir, file_name)
        if not os.path.exists(dest_file):
            if getattr(sys, 'frozen', False):
                # Copy from the bundled resources
                source_file = os.path.join(sys._MEIPASS, 'json', file_name)
            else:
                # Copy from the script directory
                source_file = os.path.join(get_app_path("json"), file_name)
            shutil.copyfile(source_file, dest_file)

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and for PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class HexDataDelegate(QStyledItemDelegate):
    """Custom delegate to handle painting and editing of Hex Data cells."""

    def __init__(self, parent=None, original_hex_values=None, opcode_keys=None):
        super().__init__(parent)
        self.original_hex_values = original_hex_values
        self.parent_widget = parent
        self.opcode_keys = opcode_keys or []

    def paint(self, painter, option, index):
        painter.save()

        # Draw background and selection
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # Get the current and original hex data
        data = index.model().data(index, Qt.DisplayRole)
        if data is None:
            painter.restore()
            return  # Avoid painting if data is None
        current_hex = data.replace(" ", "")
        row = index.row()
        original_hex = self.original_hex_values.get(row, "").replace(" ", "")

        # Set font
        font = option.font
        painter.setFont(font)
        fm = QFontMetrics(font)

        # Calculate text position
        x = option.rect.x() + 5  # Add some padding
        y = int(option.rect.y() + fm.ascent() + (option.rect.height() - fm.height()) / 2)

        # Split hex data into bytes
        current_bytes = [current_hex[i:i+2] for i in range(0, len(current_hex), 2)]
        original_bytes = [original_hex[i:i+2] for i in range(0, len(original_hex), 2)]

        # Calculate the width of one byte plus a space
        byte_text = "00 "
        byte_width = fm.width(byte_text)

        # For each byte, compare with original and set color accordingly
        for i, byte in enumerate(current_bytes):
            if i < len(original_bytes) and byte != original_bytes[i]:
                painter.setPen(QColor("red"))
            else:
                if option.state & QStyle.State_Selected:
                    painter.setPen(option.palette.highlightedText().color())
                else:
                    painter.setPen(option.palette.text().color())

            # Draw byte
            painter.drawText(x, y, byte)
            # Move x position
            x += byte_width  # Move x position by the width of one byte plus a space

        painter.restore()

    def createEditor(self, parent, option, index):
        # Create a line edit for editing hex data
        editor = QLineEdit(parent)
        editor.setFont(option.font)

        # Auto-completion for hex data
        model = QStandardItemModel()
        for key in self.opcode_keys:
            item = QStandardItem(key)
            model.appendRow(item)
        completer = QCompleter(model)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        editor.setCompleter(completer)

        return editor

    def setEditorData(self, editor, index):
        # Set the text in the editor
        text = index.model().data(index, Qt.EditRole)
        editor.setText(text)

    def setModelData(self, editor, model, index):
        # Get the text from the editor
        text = editor.text().replace(" ", "").upper()
        # Validate hex data
        if all(c in '0123456789ABCDEF' for c in text):
            # Update the model data
            formatted_text = " ".join(text[i:i+2] for i in range(0, len(text), 2))
            model.setData(index, formatted_text, Qt.EditRole)
            # After editing, repaint the cell
            rect = self.parent_widget.visualRect(index)
            self.parent_widget.viewport().update(rect)
        else:
            # Show an error message
            self.show_error_message("Invalid Input", "Please enter valid hexadecimal values (0-9, A-F).")
            # Revert to the original text
            editor.setText(index.model().data(index, Qt.DisplayRole))

    def show_error_message(self, title, message):
        """Displays an error message using the parent's style."""
        msg_box = QMessageBox(self.parent_widget)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(self.parent_widget.styleSheet())
        self.parent_widget.apply_palette_to_widget(msg_box)
        msg_box.exec_()

class DraggableTableWidget(QTableWidget):
    """Custom QTableWidget that supports row dragging and custom key events."""
    def __init__(self, *args, **kwargs):
        super(DraggableTableWidget, self).__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dropEvent(self, event):
        source_row = self.currentRow()
        target_row = self.rowAt(event.pos().y())

        if target_row == -1:
            target_row = self.rowCount() - 1

        if source_row != target_row:
            # Create a deep copy of the source row
            row_data = []
            for column in range(self.columnCount()):
                item = self.item(source_row, column)
                if item is not None:
                    new_item = QTableWidgetItem(item)
                    row_data.append(new_item)
                else:
                    row_data.append(QTableWidgetItem())

            # Insert the copied row at the target position
            self.insertRow(target_row)
            for column, item in enumerate(row_data):
                self.setItem(target_row, column, item)

            # Remove the original row
            if source_row > target_row:
                self.removeRow(source_row + 1)
            else:
                self.removeRow(source_row)
        event.accept()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.window().copy_hex_data()
        else:
            super().keyPressEvent(event)

class NonEditableDelegate(QStyledItemDelegate):
    """Delegate to prevent editing of specific table columns."""
    def createEditor(self, parent, option, index):
        # Prevent editing by returning None
        return None

class SCDOpcodeHelper(QMainWindow):
    """Main window class for the SCD Opcode Helper application."""
    def __init__(self):
        """Initialize the main window and set up the UI."""
        super().__init__()
        self.setWindowTitle("CRE SCD BHS v0.7b")
        icon_path = resource_path("Blue.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(100, 100, 1475, 600)

        # Load themes and settings
        self.themes = load_themes()
        self.settings = QSettings('MyCompany', 'SCDOpcodeHelper')
        self.current_theme_name = self.settings.value('theme', 'Dark')
        if self.current_theme_name not in self.themes:
            self.current_theme_name = 'Dark'  # Fallback to 'Dark' theme if not found
        self.setStyleSheet(dict_to_stylesheet(self.themes[self.current_theme_name]))
        logging.info(f"Initialized with theme: {self.current_theme_name}")

        # Clipboard for copy/paste
        self.clipboard = QApplication.clipboard()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Store original values to compare changes
        self.original_hex_values = {}

        # Main widget and layout
        widget = QWidget()
        main_layout = QHBoxLayout()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        # Left layout for buttons
        left_button_layout = QVBoxLayout()
        main_layout.addLayout(left_button_layout)

        left_button_layout.addStretch()

        # Move Up Button
        self.move_up_button = QPushButton(self)
        self.move_up_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.move_up_button.setToolTip("Move Row Up")
        self.move_up_button.setFixedSize(30, 30)
        self.move_up_button.clicked.connect(self.move_row_up)
        left_button_layout.addWidget(self.move_up_button)

        # Move Down Button
        self.move_down_button = QPushButton(self)
        self.move_down_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.move_down_button.setToolTip("Move Row Down")
        self.move_down_button.setFixedSize(30, 30)
        self.move_down_button.clicked.connect(self.move_row_down)
        left_button_layout.addWidget(self.move_down_button)

        # Add Row Button
        self.add_row_button = QPushButton(self)
        self.add_row_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.add_row_button.setToolTip("Add a New Row")
        self.add_row_button.setFixedSize(30, 30)
        self.add_row_button.clicked.connect(self.add_row)
        left_button_layout.addWidget(self.add_row_button)

        # Spacer between top and bottom buttons
        left_button_layout.addSpacing(20)

        # Button 1: Copy All
        self.copy_all_button = QPushButton(self)
        self.copy_all_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.copy_all_button.setToolTip("Copy All Data")
        self.copy_all_button.setFixedSize(30, 30)
        self.copy_all_button.clicked.connect(self.copy_all_data)
        left_button_layout.addWidget(self.copy_all_button)

        # Button 2: Copy Hex
        self.copy_hex_button = QPushButton(self)
        self.copy_hex_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))  # Original copying icon
        self.copy_hex_button.setToolTip("Copy Hex Data")
        self.copy_hex_button.setFixedSize(30, 30)
        self.copy_hex_button.clicked.connect(self.copy_all_hex_data)
        left_button_layout.addWidget(self.copy_hex_button)

        # Button 3: Export as CSV
        self.export_csv_button = QPushButton(self)
        self.export_csv_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))  # Original Excel icon
        self.export_csv_button.setToolTip("Export as CSV")
        self.export_csv_button.setFixedSize(30, 30)
        self.export_csv_button.clicked.connect(self.export_as_csv)
        left_button_layout.addWidget(self.export_csv_button)

        left_button_layout.addStretch()

        # Right layout for game dropdown and table
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)

        # Top layout for game selection dropdown and buttons
        top_layout = QHBoxLayout()
        right_layout.addLayout(top_layout)

        # Dropdown for game selection
        self.dropdown = self.create_game_dropdown()
        top_layout.addWidget(self.dropdown, alignment=Qt.AlignLeft)

        # Spacer between dropdown and buttons
        top_layout.addStretch()

        # Title Label with mixed fonts and colors
        font = QFont("Brush Script MT", 20, QFont.Bold)
        title_label = QLabel("Classic ")
        title_label.setFont(font)
        title_label.setStyleSheet("color: grey;")

        title_label2 = QLabel("Resident Evil")
        title_label2.setFont(font)
        title_label2.setStyleSheet("color: #FF6F61;")

        title_label3 = QLabel(" SCD Build Helper Suite ")
        title_label3.setFont(font)
        title_label3.setStyleSheet("color: grey;")

        version_label = QLabel("v0.7b")
        version_label.setFont(font)
        version_label.setStyleSheet("color: #FF6F61;")

        title_layout = QHBoxLayout()
        title_layout.addWidget(title_label)
        title_layout.addWidget(title_label2)
        title_layout.addWidget(title_label3)
        title_layout.addWidget(version_label)

        top_layout.addLayout(title_layout)

        top_layout.addStretch()

        # Load and save buttons (aligned to the right)
        self.load_button = self.create_load_button()
        top_layout.addWidget(self.load_button, alignment=Qt.AlignRight)

        self.save_button = self.create_save_button()
        top_layout.addWidget(self.save_button, alignment=Qt.AlignRight)

        # Opcode Editor Button
        self.opcode_editor_button = self.create_opcode_editor_button()
        top_layout.addWidget(self.opcode_editor_button, alignment=Qt.AlignRight)

        # Create the table widget inside a scroll area
        self.table_scroll_area = QScrollArea()
        self.table_scroll_area.setWidgetResizable(True)
        self.table_widget = DraggableTableWidget()
        self.table_widget.setColumnCount(3)  # Opcode Name, Hex Data, and Description
        self.table_widget.setHorizontalHeaderLabels(['Opcode Name', 'Hex Data', 'Description'])
        self.table_widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table_scroll_area.setWidget(self.table_widget)
        right_layout.addWidget(self.table_scroll_area)

        # Set font to accommodate 38 bytes
        opcode_font = QFont("Courier New", 8)
        self.table_widget.setFont(opcode_font)

        self.table_widget.itemChanged.connect(lambda item: self.track_changes(item))

        header = self.table_widget.horizontalHeader()
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("QHeaderView::section { background-color: #000000; color: #ffffff; }")

        # Set custom column widths and resize modes
        self.set_column_widths({
            0: 120,  # Opcode Name
            1: None,  # Hex Data (fixed width calculated below)
            2: None   # Description (stretch to fill)
        })

        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # Calculate desired width for 38 bytes
        fm = QFontMetrics(self.table_widget.font())
        byte_text = "00 "
        byte_width = fm.width(byte_text)
        desired_width_for_38_bytes = byte_width * 38 + 10  # +10 for padding
        self.table_widget.setColumnWidth(1, desired_width_for_38_bytes)

        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Set selection mode to allow multiple selection
        self.table_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectItems)

        # Disable editing for opcode name and description columns
        self.table_widget.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table_widget.setItemDelegateForColumn(0, NonEditableDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(2, NonEditableDelegate(self.table_widget))

        # Set the custom delegate for the hex data column
        self.hex_delegate = HexDataDelegate(self.table_widget, self.original_hex_values)
        self.table_widget.setItemDelegateForColumn(1, self.hex_delegate)

        # Initialize the data
        self.current_opcodes = {}
        # Set default path to user's home directory
        self.last_loaded_path = os.path.expanduser("~")
        self.last_valid_hex = {}

        self.dropdown.currentIndexChanged.connect(self.game_selected)

        # Enable hover detection for the hex data column
        self.table_widget.viewport().installEventFilter(self)

        # Create the menu using the helper
        create_menu(self)

        # Context menu for hex data column
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        # Connect cell click to handle opening links
        self.table_widget.cellClicked.connect(self.handle_cell_click)

        # Set up copy action for Ctrl+C
        copy_action = QAction(self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_hex_data)
        self.addAction(copy_action)

        logging.info("Main window initialized.")

    def set_column_widths(self, widths):
        """Sets custom widths for the table columns."""
        for col, width in widths.items():
            if width is not None:
                self.table_widget.setColumnWidth(col, width)
        logging.info(f"Column widths set: {widths}")

    def create_game_dropdown(self):
        """Creates the game selection dropdown."""
        dropdown = QComboBox()
        dropdown.addItem("Select Game")
        available_games = ["Resident Evil 1", "Resident Evil 1.5", "Resident Evil 2", "Resident Evil 3"]
        dropdown.addItems(available_games)
        dropdown.setCurrentIndex(0)  # Set 'Select Game' as default
        dropdown.setFixedWidth(200)
        dropdown.setToolTip("Select a game to load its opcodes.")
        logging.info("Game dropdown created with options.")
        return dropdown

    def create_load_button(self):
        """Creates the Load SCD button."""
        button = QPushButton('Load SCD')
        button.clicked.connect(self.load_scd_file)
        button.setFixedWidth(100)
        logging.info("Load button created.")
        return button

    def create_save_button(self):
        """Creates the Save SCD button."""
        button = QPushButton('Save SCD')
        button.clicked.connect(self.save_scd_file)
        button.setFixedWidth(100)
        logging.info("Save button created.")
        return button

    def create_opcode_editor_button(self):
        """Creates the Opcode Editor button."""
        button = QPushButton('Opcode Editor')
        button.clicked.connect(lambda: open_opcode_editor(self))
        button.setFixedWidth(150)
        logging.info("Opcode Editor button created.")
        return button

    def move_row_up(self):
        """Moves the selected row up."""
        logging.info("Moving row up.")
        move_row_up(self)
        self.apply_row_formatting()

    def move_row_down(self):
        """Moves the selected row down."""
        logging.info("Moving row down.")
        move_row_down(self)
        self.apply_row_formatting()

    def add_row(self):
        """Adds a new empty row to the table."""
        row_position = self.table_widget.rowCount()
        logging.info(f"Adding new row at position: {row_position}")
        self.table_widget.insertRow(row_position)
        # Add empty items to prevent errors
        self.table_widget.setItem(row_position, 0, QTableWidgetItem(""))
        self.table_widget.setItem(row_position, 1, QTableWidgetItem(""))
        self.table_widget.setItem(row_position, 2, QTableWidgetItem(""))

    def apply_row_formatting(self):
        """Applies formatting to the Opcode Name column after moving rows."""
        for row in range(self.table_widget.rowCount()):
            opcode_item = self.table_widget.item(row, 0)
            if opcode_item:
                opcode_item.setTextAlignment(Qt.AlignCenter)
                font = QFont()
                font.setItalic(True)
                opcode_item.setFont(font)

    def game_selected(self):
        """Handles the event when a game is selected from the dropdown."""
        if self.dropdown.currentIndex() == 0:
            logging.info("No game selected.")
            self.current_opcodes = {}
            self.dropdown.setToolTip("Please select a game from the list.")
            return

        # Check for unsaved changes and prompt the user
        if self.has_unsaved_changes():
            reply = self.show_unsaved_changes_dialog()
            if reply == QMessageBox.Yes:
                self.save_scd_file()  # Save changes if user selects "Yes"
            elif reply == QMessageBox.Cancel:
                self.dropdown.setCurrentIndex(0)  # Revert selection
                return  # Do nothing if user selects "Cancel"

        # Clear current table and opcodes
        self.table_widget.setRowCount(0)
        self.original_hex_values.clear()

        game = self.dropdown.currentText()
        logging.info(f"Selected game: {game}")
        self.current_opcodes = self.load_opcode_data(game)
        self.dropdown.setToolTip(f"Selected game: {game}")
        # Update the opcode keys for auto-completion
        # Flatten the opcode names for auto-completion
        opcode_keys = []
        for opcode_list in self.current_opcodes.values():
            for key, opcode_info in opcode_list:
                opcode_keys.append(opcode_info["Opcode Name"])
        self.hex_delegate.opcode_keys = opcode_keys

    def show_unsaved_changes_dialog(self):
        """Displays a dialog for unsaved changes."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Unsaved Changes")
        msg_box.setText("You have unsaved changes. Do you want to save before loading a new game?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        msg_box.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(msg_box)
        return msg_box.exec_()

    def has_unsaved_changes(self):
        """Check if there are any unsaved changes by comparing current and original hex values."""
        for row in range(self.table_widget.rowCount()):
            hex_data_item = self.table_widget.item(row, 1)
            if hex_data_item:
                current_value = hex_data_item.text().replace(" ", "")
                original_value = self.original_hex_values.get(row, "").replace(" ", "")
                if current_value != original_value:
                    return True
        return False

    def load_opcode_data(self, game):
        """Loads opcode data for the selected game."""
        logging.info(f"Loading opcodes for game: {game}")
        game_file_map = {
            "Resident Evil 1": "re1_opcodes.json",
            "Resident Evil 1.5": "re15_opcodes.json",
            "Resident Evil 2": "re2_opcodes.json",
            "Resident Evil 3": "re3_opcodes.json"
        }
        file_name = game_file_map.get(game)
        if file_name:
            json_dir = get_app_path("json")
            full_path = os.path.join(json_dir, file_name)
            logging.info(f"Full opcode file path: {full_path}")
            try:
                with open(full_path, 'r', encoding='utf-8') as json_file:
                    opcodes = json.load(json_file)
                    # Parse using parse_opcodes_as_dict for all games
                    parsed_opcodes = self.parse_opcodes_as_dict(opcodes, game)
                    logging.info("Opcodes loaded and parsed successfully.")
                    return parsed_opcodes
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(f"Error loading opcode data: {e}")
                self.show_error_message("Error", f"Failed to load opcode data: {e}")
        return {}

    def parse_opcodes_as_dict(self, opcodes, game):
        """Parses opcode data from a dictionary for all games.

        Returns a mapping from Opcode Number to list of tuples (key, opcode_info).
        """
        logging.info("Parsing opcodes as dictionary for all games.")
        parsed_opcodes = {}
        for key, opcode_info in opcodes.items():
            opcode_number = opcode_info.get("Opcode Number")
            if not opcode_number:
                logging.warning(f"Opcode entry {key} missing 'Opcode Number'. Skipping.")
                continue
            if opcode_number not in parsed_opcodes:
                parsed_opcodes[opcode_number] = []
            parsed_opcodes[opcode_number].append((key, opcode_info))  # Store key and opcode_info
        logging.info("Opcodes parsed successfully.")
        return parsed_opcodes

    def load_scd_file(self):
        """Loads an SCD file and parses its data."""
        if self.dropdown.currentIndex() == 0:
            self.show_error_message("No Game Selected", "Please select a game before loading an SCD file.")
            return
        options = QFileDialog.Options()
        file_dialog = QFileDialog(self, "Open SCD File", self.last_loaded_path, "SCD Files (*.scd);;All Files (*)")
        file_dialog.setOptions(options)
        file_dialog.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(file_dialog)
        if file_dialog.exec_():
            file_name = file_dialog.selectedFiles()[0]
            if file_name:
                logging.info(f"Loading SCD file: {file_name}")
                try:
                    self.table_widget.blockSignals(True)
                    with open(file_name, 'rb') as file:
                        binary_data = file.read()
                        hex_data = binary_data.hex().upper()
                    self.last_loaded_path = os.path.dirname(file_name)
                    logging.info(f"File loaded successfully: {file_name}")
                except FileNotFoundError:
                    logging.error(f"File not found: {file_name}")
                    self.show_error_message("Error", f"File not found: {file_name}")
                    return
                except PermissionError:
                    logging.error(f"Permission denied: {file_name}")
                    self.show_error_message("Error", f"Permission denied: {file_name}")
                    return
                except Exception as e:
                    logging.error(f"Error loading file: {e}")
                    self.show_error_message("Error", f"Failed to load SCD file: {e}")
                    return

                self.parse_scd_data(hex_data)
                self.table_widget.blockSignals(False)

    def parse_scd_data(self, hex_data):
        """Parses the hex data from the SCD file and populates the table."""
        logging.info("Parsing SCD file data.")
        self.table_widget.setRowCount(0)
        self.original_hex_values.clear()

        # Get the text color from the current theme and invert it
        table_style = self.themes[self.current_theme_name].get("QTableWidget", {})
        text_color = table_style.get("color", "#000000")
        text_qcolor = QColor(text_color)
        inverted_color = QColor(255 - text_qcolor.red(), 255 - text_qcolor.green(), 255 - text_qcolor.blue())

        position = 0
        unknown_opcodes = []
        game = self.dropdown.currentText()
        while position < len(hex_data):
            opcode_hex = hex_data[position:position + 2]
            logging.info(f"Processing opcode: {opcode_hex} at position {position}")
            if opcode_hex in self.current_opcodes:
                opcode_info_list = self.current_opcodes[opcode_hex]
                selected_opcode_info = None

                # Special handling for Resident Evil 1.5 and specific opcodes (2C, 3B, 50)
                if game == "Resident Evil 1.5" and opcode_hex.upper() in ["2C", "3B", "50"]:
                    # Ensure enough data is available to read Byte 4 (SAT)
                    min_length = 8  # Opcode + at least 3 bytes to reach SAT
                    if position + min_length > len(hex_data):
                        logging.error(f"Insufficient hex data to read Byte 4 for opcode {opcode_hex} at position {position}")
                        break
                    # Extract Byte 4 (SAT)
                    byte4_hex = hex_data[position + 6:position + 8]
                    sat_value = int(byte4_hex, 16)

                    logging.info(f"Opcode {opcode_hex} Byte 4 (SAT): 0x{byte4_hex} (decimal: {sat_value})")

                    # Select the correct opcode_info based on SAT byte comparison
                    if sat_value > 0x31:
                        # Find the '_4p' version
                        for key, info in opcode_info_list:
                            if info["Opcode Name"].endswith("_4p"):
                                selected_opcode_info = info
                                break
                    else:
                        # Use the standard version
                        for key, info in opcode_info_list:
                            if not info["Opcode Name"].endswith("_4p"):
                                selected_opcode_info = info
                                break
                    if not selected_opcode_info:
                        logging.error(f"Failed to select correct opcode for {opcode_hex} with SAT 0x{byte4_hex}")
                        break

                    # Now get the opcode_length from selected_opcode_info
                    try:
                        opcode_length = int(selected_opcode_info["Opcode Length"].split()[0])
                    except (ValueError, IndexError):
                        logging.error(f"Invalid Opcode Length for opcode {opcode_hex}: {selected_opcode_info['Opcode Length']}")
                        break

                    total_length_in_hex = opcode_length * 2

                    # Ensure enough data is available to read the full opcode
                    if position + total_length_in_hex > len(hex_data):
                        logging.error(f"Insufficient hex data for opcode {opcode_hex} at position {position}")
                        break

                else:
                    # Not a special opcode or not Resident Evil 1.5
                    selected_opcode_info = opcode_info_list[0][1]  # Default to the first entry

                    # Determine opcode length
                    try:
                        opcode_length = int(selected_opcode_info["Opcode Length"].split()[0])
                    except (ValueError, IndexError):
                        logging.error(f"Invalid Opcode Length for opcode {opcode_hex}: {selected_opcode_info['Opcode Length']}")
                        break

                    total_length_in_hex = opcode_length * 2

                    # Ensure enough data is available to read the full opcode
                    if position + total_length_in_hex > len(hex_data):
                        logging.error(f"Insufficient hex data for opcode {opcode_hex} at position {position}")
                        break

                opcode_full_hex = hex_data[position:position + total_length_in_hex].upper()

                grouped_hex = " ".join(opcode_full_hex[i:i + 2] for i in range(0, len(opcode_full_hex), 2))

                row_position = self.table_widget.rowCount()
                self.table_widget.insertRow(row_position)

                opcode_name = selected_opcode_info["Opcode Name"]
                opcode_item = QTableWidgetItem(opcode_name)
                opcode_item.setFlags(opcode_item.flags() & ~Qt.ItemIsEditable)
                opcode_item.setFont(self.get_opcode_font())
                opcode_item.setTextAlignment(Qt.AlignCenter)
                self.table_widget.setItem(row_position, 0, opcode_item)

                hex_data_item = QTableWidgetItem(grouped_hex)
                hex_data_item.setForeground(QBrush(inverted_color))
                self.table_widget.setItem(row_position, 1, hex_data_item)

                self.original_hex_values[row_position] = grouped_hex

                description_item = QTableWidgetItem(selected_opcode_info["Opcode Description"])
                description_item.setFlags(description_item.flags() & ~Qt.ItemIsEditable)
                description_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left alignment for Description
                self.table_widget.setItem(row_position, 2, description_item)

                position += total_length_in_hex
            else:
                logging.warning(f"Unknown Opcode: {opcode_hex}, skipping 2 hex digits at position {position}")
                unknown_opcodes.append((opcode_hex, position))
                position += 2

        if unknown_opcodes:
            message = "Unknown opcodes encountered at positions:\n"
            for opcode, pos in unknown_opcodes:
                message += f"Opcode {opcode} at position {pos}\n"
            self.show_error_message("Unknown Opcodes", message)
            logging.warning(message)

        logging.info("Finished parsing SCD file.")

        # Apply formatting after parsing
        self.apply_row_formatting()

    def get_opcode_font(self):
        """Returns the font used for the opcode name."""
        font = QFont()
        font.setBold(True)
        font.setItalic(True)
        return font

    def eventFilter(self, source, event):
        """Custom event filter to detect mouse hovering over the hex data and show byte-specific tooltip."""
        if event.type() == QEvent.ToolTip and source == self.table_widget.viewport():
            pos = self.table_widget.viewport().mapFromGlobal(event.globalPos())
            item = self.table_widget.itemAt(pos)
            if item and item.column() == 1:  # Only handle Hex Data column
                hex_data = item.text().replace(" ", "")
                row = item.row()

                if len(hex_data) < 2:
                    return False  # Invalid hex data length

                # Fetch the opcode based on the first two characters (the opcode number)
                opcode_hex = hex_data[:2]  # The first two characters represent the opcode
                byte_structure = None
                # Find the opcode_info corresponding to this row
                opcode_name_item = self.table_widget.item(row, 0)
                if opcode_name_item:
                    opcode_name = opcode_name_item.text()
                    # Search in current_opcodes for this opcode_name
                    for op_list in self.current_opcodes.values():
                        for key, op_info in op_list:
                            if op_info["Opcode Name"] == opcode_name:
                                byte_structure = op_info.get("Bytes", {})
                                break
                        if byte_structure:
                            break

                if byte_structure:
                    byte_info = byte_structure

                    # Calculate the index of the byte being hovered over
                    font = self.table_widget.font()
                    fm = QFontMetrics(font)
                    byte_text = "00 "
                    byte_width = fm.width(byte_text)
                    # Adjust for padding
                    x_offset = pos.x() - self.table_widget.columnViewportPosition(1) - 5  # Subtract the same padding added in paint()
                    byte_index = int(x_offset / byte_width)

                    # Ensure the index is within the range of the hex data
                    if 0 <= byte_index < len(hex_data) // 2:
                        byte_value = hex_data[byte_index * 2:(byte_index + 1) * 2]
                        byte_name, byte_description = self.get_byte_info(byte_info, byte_index)

                        # Construct the tooltip message with byte-specific details
                        tooltip_text = f"Byte {byte_index + 1}: {byte_value} ({byte_name})\nDescription: {byte_description}"
                        QToolTip.showText(event.globalPos(), tooltip_text)
                        return True
        return super().eventFilter(source, event)

    def get_byte_info(self, byte_info, byte_index):
        """Fetches byte name and description based on the byte index in the opcode structure."""
        byte_position = byte_index + 1  # Adjust for human-readable 1-based indexing

        # Iterate over each byte field in the opcode structure
        current_byte_count = 0
        for byte_name, details in byte_info.items():
            byte_type = details.get("Type", "")
            byte_length = 1 if byte_type in ["UCHAR", "CHAR"] else 2  # Adjust based on byte type

            # Calculate byte range
            byte_range = range(current_byte_count + 1, current_byte_count + byte_length + 1)

            # Check if byte_position falls within this byte range
            if byte_position in byte_range:
                return byte_name, details.get("Description", "No description available")

            # Move the current byte count forward by the length of this byte field
            current_byte_count += byte_length

        return "Unknown", "No description available"

    def track_changes(self, item):
        """Tracks changes in the Hex Data column and updates related cells."""
        if item.column() == 1:  # Only check the Hex Data column
            row = item.row()
            current_value = item.text().replace(" ", "").upper()
            original_value = self.original_hex_values.get(row, "").replace(" ", "").upper()
            prev_value = item.data(Qt.UserRole)
            if prev_value is None:
                prev_value = original_value

            # Validate hex data
            if not all(c in '0123456789ABCDEF' for c in current_value):
                self.show_error_message("Invalid Input", "Please enter valid hexadecimal values (0-9, A-F).")
                item.setText(prev_value)
                return

            # Store the change in the undo stack
            self.undo_stack.append((row, item.column(), prev_value))
            # Clear the redo stack
            self.redo_stack.clear()

            # Set the new value as the current data
            item.setData(Qt.UserRole, current_value)

            # Update opcode name and description
            hex_data = current_value
            if len(hex_data) >= 2:
                first_two_bytes = hex_data[:2]
                if first_two_bytes in self.current_opcodes:
                    opcode_info_list = self.current_opcodes[first_two_bytes]
                    selected_opcode_info = opcode_info_list[0][1]  # Get opcode_info from the tuple

                    # Update opcode name
                    opcode_item = self.table_widget.item(row, 0)
                    if opcode_item:
                        opcode_item.setText(selected_opcode_info["Opcode Name"])
                        opcode_item.setTextAlignment(Qt.AlignCenter)
                        font = QFont()
                        font.setItalic(True)
                        opcode_item.setFont(font)

                    # Update description
                    description_item = self.table_widget.item(row, 2)
                    if description_item:
                        description_item.setText(selected_opcode_info["Opcode Description"])
                        description_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    # Handle Unknown opcode
                    unknown_item = self.table_widget.item(row, 0)
                    if unknown_item:
                        unknown_item.setText("Unknown")
                        unknown_item.setTextAlignment(Qt.AlignCenter)
                        font = QFont()
                        font.setItalic(True)
                        unknown_item.setFont(font)
                    unknown_desc = self.table_widget.item(row, 2)
                    if unknown_desc:
                        unknown_desc.setText("")
                        unknown_desc.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Trigger the delegate to repaint
            rect = self.table_widget.visualRect(self.table_widget.model().index(row, item.column()))
            self.table_widget.viewport().update(rect)

    def copy_hex_data(self):
        """Copies selected hex data cells to the clipboard."""
        selection = self.table_widget.selectedIndexes()
        if selection:
            # Filter for hex data column (column 1)
            hex_data_indices = [index for index in selection if index.column() == 1]
            # Sort indices by row order
            hex_data_indices.sort(key=lambda index: index.row())
            copied_data = ''
            for index in hex_data_indices:
                item = self.table_widget.item(index.row(), 1)
                if item:
                    copied_data += item.text() + '\n'
            self.clipboard.setText(copied_data.strip())
            logging.info(f"Copied hex data: {copied_data}")

    def copy_all_data(self):
        """Copies all table data to the clipboard."""
        row_count = self.table_widget.rowCount()
        column_count = self.table_widget.columnCount()
        copied_data = ''
        headers = [self.table_widget.horizontalHeaderItem(i).text() for i in range(column_count)]
        copied_data += '\t'.join(headers) + '\n'
        for row in range(row_count):
            row_data = []
            for col in range(column_count):
                item = self.table_widget.item(row, col)
                if item:
                    row_data.append(item.text())
                else:
                    row_data.append('')
            copied_data += '\t'.join(row_data) + '\n'
        self.clipboard.setText(copied_data.strip())
        logging.info("Copied all data to clipboard")

    def copy_all_hex_data(self):
        """Copies all hex data to the clipboard."""
        row_count = self.table_widget.rowCount()
        copied_data = ''
        for row in range(row_count):
            item = self.table_widget.item(row, 1)  # Hex Data column
            if item:
                copied_data += item.text() + '\n'
        self.clipboard.setText(copied_data.strip())
        logging.info("Copied all hex data to clipboard")

    def export_as_csv(self):
        """Exports the table data to a CSV file."""
        options = QFileDialog.Options()
        file_dialog = QFileDialog(self, "Save CSV File", self.last_loaded_path, "CSV Files (*.csv);;All Files (*)")
        file_dialog.setOptions(options)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(file_dialog)
        if file_dialog.exec_():
            file_name = file_dialog.selectedFiles()[0]
            if file_name:
                if not file_name.endswith('.csv'):
                    file_name += '.csv'
                try:
                    with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        # Write headers
                        headers = [self.table_widget.horizontalHeaderItem(i).text() for i in range(self.table_widget.columnCount())]
                        writer.writerow(headers)
                        # Write data rows
                        for row in range(self.table_widget.rowCount()):
                            row_data = []
                            for col in range(self.table_widget.columnCount()):
                                item = self.table_widget.item(row, col)
                                if item:
                                    row_data.append(item.text())
                                else:
                                    row_data.append('')
                            writer.writerow(row_data)
                    logging.info(f"Exported data to CSV file: {file_name}")
                    self.show_info_message("Success", f"Data exported to CSV file: {file_name}")
                except Exception as e:
                    logging.error(f"Error exporting to CSV: {e}")
                    self.show_error_message("Error", f"Failed to export to CSV file: {e}")

    def undo_hex_data(self):
        """Undoes the last hex data change."""
        if self.undo_stack:
            row, col, prev_value = self.undo_stack.pop()
            current_item = self.table_widget.item(row, col)
            # Push the current value onto the redo stack
            current_value = current_item.text()
            self.redo_stack.append((row, col, current_value))
            logging.info(f"Undoing changes in row {row}, column {col}. Restoring value to: {prev_value}")
            current_item.setText(prev_value)
            # Update the data
            self.track_changes(current_item)

    def redo_hex_data(self):
        """Redoes the last undone hex data change."""
        if self.redo_stack:
            row, col, prev_value = self.redo_stack.pop()
            current_item = self.table_widget.item(row, col)
            # Push the current value onto the undo stack
            current_value = current_item.text()
            self.undo_stack.append((row, col, current_value))
            logging.info(f"Redoing changes in row {row}, column {col}. Setting value to: {prev_value}")
            current_item.setText(prev_value)
            # Update the data
            self.track_changes(current_item)

    def add_theme_menu(self, menu):
        """Adds the theme selection menu to the menubar."""
        for theme_name in self.themes.keys():
            if theme_name != 'BaseTheme':  # Exclude BaseTheme from the menu
                theme_action = QAction(theme_name, self)
                theme_action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
                menu.addAction(theme_action)
        logging.info("Theme menu added to the menubar.")

    def apply_theme(self, theme_name):
        """Applies the selected theme."""
        theme_style = self.themes[theme_name]
        stylesheet = dict_to_stylesheet(theme_style)
        self.setStyleSheet(stylesheet)
        self.current_theme_name = theme_name
        self.settings.setValue('theme', theme_name)
        logging.info("Applied new theme.")

    def edit_current_theme(self):
        """Opens the theme editor to edit the current theme."""
        from theme_editor import ThemeEditor
        theme_name = self.current_theme_name
        theme_style = self.themes[theme_name]
        editor = ThemeEditor(self, theme_name, theme_style)
        if editor.exec_():
            new_theme_name, new_theme_style = editor.get_new_theme()
            # Save the new theme
            self.themes[new_theme_name] = new_theme_style
            # Save themes to themes.json
            json_dir = get_app_path("json")
            themes_path = os.path.join(json_dir, 'themes.json')
            with open(themes_path, 'w') as file:
                json.dump(self.themes, file, indent=4)
            # Reload themes from themes.json
            self.themes = load_themes()
            # Update the theme menu
            theme_menu = self.menuBar().findChild(QMenu, 'ThemeMenu')
            if theme_menu is not None:
                theme_menu.clear()
                self.add_theme_menu(theme_menu)
                # Apply the new theme
                self.apply_theme(new_theme_name)
                self.current_theme_name = new_theme_name
            else:
                logging.error("Error: Theme menu not found.")

    def show_context_menu(self, position):
        """Shows the context menu for the table."""
        index = self.table_widget.indexAt(position)
        if index.isValid():
            menu = QMenu()
            copy_action = QAction("Copy", self)
            copy_action.triggered.connect(self.copy_hex_data)
            paste_action = QAction("Paste", self)
            paste_action.triggered.connect(self.paste_hex_data)
            menu.addAction(copy_action)
            menu.addAction(paste_action)
            menu.setStyleSheet(self.styleSheet())
            self.apply_palette_to_widget(menu)
            menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def show_instructions(self):
        """Displays the instructions dialog."""
        instructions_dialog = QDialog(self)
        instructions_dialog.setWindowTitle("Instructions")
        instructions_dialog.setStyleSheet(self.styleSheet())

        # Apply palette
        self.apply_palette_to_widget(instructions_dialog)

        # Set up layout and content
        layout = QVBoxLayout(instructions_dialog)
        instructions_label = QLabel("""
        <html>
        <head>
        <style>
        body { font-family: Arial; }
        h2 { color: #2E8B57; }
        ul { margin-left: -20px; margin-top: 10px; margin-bottom: 10px; }
        li { margin-bottom: 10px; }  /* Add space between list items */
        </style>
        </head>
        <body>
        <h2>Instructions</h2>
        <ul>
        <li><b>Selecting a Game:</b> Use the dropdown menu to select a Resident Evil game to load its opcodes.</li>
        <li><b>Loading SCD Files:</b> Click 'Load SCD' to open and load an SCD file associated with the selected game.</li>
        <li><b>Editing Hex Data:</b> Double-click on the 'Hex Data' cell to edit. Only valid hexadecimal values (0-9, A-F) are allowed.</li>
        <li><b>Opcode Editor:</b> Click 'Opcode Editor' to edit opcodes for the selected game.</li>
        <li><b>Moving Rows:</b> Use the up/down arrow buttons or drag and drop rows to reorder them.</li>
        <li><b>Adding Rows:</b> Click the '+' button to add a new empty row to the table.</li>
        <li><b>Copying Data:</b> Use the copy buttons to copy all data or hex data to the clipboard.</li>
        <li><b>Exporting as CSV:</b> Click the export button to save the table data as a CSV file.</li>
        <li><b>Saving SCD Files:</b> Click 'Save SCD' to save your changes to a new or existing SCD file.</li>
        <li><b>Undo/Redo:</b> Use 'Undo' and 'Redo' from the 'Edit' menu or use Ctrl+Z and Ctrl+Y to undo or redo changes.</li>
        <li><b>Themes:</b> Change themes or edit the current theme from the 'Theme' menu.</li>
        <li><b>Copy/Paste in Cells:</b> Right-click on a cell or use the 'Edit' menu to copy or paste data.</li>
        <li><b>Viewing Opcode Documentation:</b> Click on an opcode name to open its documentation link (if available).</li>
        <li><b>Byte Tooltips:</b> Hover over bytes in the 'Hex Data' column to see detailed information about each byte.</li>
        <li><b>Scrollbars:</b> Use the scrollbar on the right to navigate through the opcodes when the window is resized.</li>
        </ul>
        <p><b>Note:</b> The 'Opcode Name' and 'Description' columns are automatically updated based on the hex data.</p>
        </body>
        </html>
        """)
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)

        instructions_dialog.exec_()

    def show_about(self):
        """Displays the about dialog."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About")
        about_dialog.setStyleSheet(self.styleSheet())

        # Apply palette
        self.apply_palette_to_widget(about_dialog)

        # Set up layout and content
        layout = QVBoxLayout(about_dialog)
        about_label = QLabel("""
        <html>
        <head>
        <style>
        body { font-family: Arial; }
        h2 { color: #2E8B57; }
        p { margin-top: 10px; }
        a { color: #1E90FF; text-decoration: none; }
        a:hover { text-decoration: underline; }
        </style>
        </head>
        <body>
        <h2>About</h2>
        <p><b>CRE SCD Editor Suite v0.7b</b></p>
        <p>This application assists in editing SCD files for classic Resident Evil games.
        It allows you to load, edit, and save SCD files, edit opcodes, and customize the application theme.</p>
        <p><b>Developer:</b> 3lric</p>
        <p><b>Links:</b></p>
        <ul>
        <li><a href="https://www.youtube.com/@3lric">YouTube</a></li>
        <li><a href="https://twitter.com/3lricM">Twitter</a></li>
        <li><a href="https://www.patreon.com/3lric">Patreon</a></li>
        <li><a href="https://classicremodification.com">Classic Resident Evil Modding (CREM) Wiki</a></li>
        </ul>
        </body>
        </html>
        """)
        about_label.setWordWrap(True)
        about_label.setOpenExternalLinks(True)  # Enable hyperlinks
        layout.addWidget(about_label)

        about_dialog.exec_()

    def show_error_message(self, title, message):
        """Displays an error message using the current theme."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(msg_box)
        msg_box.exec_()

    def show_info_message(self, title, message):
        """Displays an information message using the current theme."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(msg_box)
        msg_box.exec_()

    def apply_palette_to_widget(self, widget):
        """Applies the current theme's palette to the given widget."""
        palette = widget.palette()
        table_style = self.themes[self.current_theme_name].get("QTableWidget", {})
        background_color = table_style.get("background-color", "")
        text_color = table_style.get("color", "")

        if background_color:
            palette.setColor(widget.backgroundRole(), QColor(background_color))
            palette.setColor(QPalette.Base, QColor(background_color))
            palette.setColor(QPalette.Window, QColor(background_color))
        if text_color:
            palette.setColor(widget.foregroundRole(), QColor(text_color))
            palette.setColor(QPalette.Text, QColor(text_color))
            palette.setColor(QPalette.ButtonText, QColor(text_color))
            palette.setColor(QPalette.WindowText, QColor(text_color))

        widget.setPalette(palette)

    def handle_cell_click(self, row, column):
        """Handles clicks on the Opcode Name column to open documentation links."""
        if column == 0:
            opcode_name = self.table_widget.item(row, column).text()
            opcode_number = None
            hex_data_item = self.table_widget.item(row, 1)
            if hex_data_item:
                hex_data = hex_data_item.text().replace(' ', '')
                opcode_number = hex_data[:2]
            if opcode_number:
                game = self.dropdown.currentText()
                if game == 'Resident Evil 2':
                    url = f'https://classicremodification.com/doku.php?id=re2_opcodes#{opcode_number}'
                    webbrowser.open(url)
                else:
                    # Handle other games or provide a default action
                    self.show_info_message("Info", f"No documentation link available for {game}.")

    def paste_hex_data(self):
        """Pastes hex data from the clipboard into selected cells."""
        current_items = self.table_widget.selectedItems()
        if current_items:
            paste_data = self.clipboard.text().split('\n')
            for item, data in zip(current_items, paste_data):
                if item.column() == 1:
                    item.setText(data)
                    self.track_changes(item)
            logging.info("Pasted data into selected cells.")

    def load_opcode_editor(self):
        """Loads the Opcode Editor."""
        open_opcode_editor(self)

    def save_scd_file(self):
        """Saves the current table data to an SCD file."""
        options = QFileDialog.Options()
        file_dialog = QFileDialog(self, "Save SCD File", self.last_loaded_path, "SCD Files (*.scd);;All Files (*)")
        file_dialog.setOptions(options)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setStyleSheet(self.styleSheet())
        self.apply_palette_to_widget(file_dialog)
        if file_dialog.exec_():
            file_name = file_dialog.selectedFiles()[0]
            if file_name:
                if not file_name.endswith('.scd'):
                    file_name += '.scd'
                try:
                    hex_data = ''
                    for row in range(self.table_widget.rowCount()):
                        item = self.table_widget.item(row, 1)
                        if item:
                            hex_data += item.text().replace(' ', '')
                    binary_data = bytes.fromhex(hex_data)
                    with open(file_name, 'wb') as file:
                        file.write(binary_data)
                    logging.info(f"Saved SCD file: {file_name}")
                    self.show_info_message("Success", f"SCD file saved: {file_name}")
                except Exception as e:
                    logging.error(f"Error saving SCD file: {e}")
                    self.show_error_message("Error", f"Failed to save SCD file: {e}")

    def load_opcodes(self, game=None, *args, **kwargs):
        """Legacy method to load opcode data.

        Accepts an optional 'game' parameter to maintain compatibility with legacy calls.
        """
        if game is None:
            game = self.dropdown.currentText()
        return self.load_opcode_data(game)

    def update_opcode_autocomplete(self):
        """Updates the opcode autocomplete in the main window.

        This method should refresh any autocomplete features that rely on the opcode data.
        """
        # Implement actual autocomplete updates here if necessary.
        logging.info("Opcode autocomplete updated.")

    def refresh_opcodes(self):
        """Re-parses and reloads the opcodes for the selected game."""
        game = self.dropdown.currentText()
        self.current_opcodes = self.load_opcode_data(game)
        # Update the opcode keys for auto-completion
        opcode_keys = []
        for opcode_list in self.current_opcodes.values():
            for key, opcode_info in opcode_list:
                opcode_keys.append(opcode_info["Opcode Name"])
        self.hex_delegate.opcode_keys = opcode_keys
        # Update the autocomplete
        self.update_opcode_autocomplete()
        # Update the opcode names and descriptions in the table
        self.update_table_opcodes()
        logging.info("Opcodes refreshed.")

    def update_table_opcodes(self):
        """Updates the opcode names and descriptions in the table based on the current hex data."""
        for row in range(self.table_widget.rowCount()):
            hex_data_item = self.table_widget.item(row, 1)
            if hex_data_item:
                hex_data = hex_data_item.text().replace(" ", "").upper()
                if len(hex_data) >= 2:
                    first_two_bytes = hex_data[:2]
                    if first_two_bytes in self.current_opcodes:
                        opcode_info_list = self.current_opcodes[first_two_bytes]
                        selected_opcode_info = opcode_info_list[0][1]
                        # Update opcode name
                        opcode_item = self.table_widget.item(row, 0)
                        if opcode_item:
                            opcode_item.setText(selected_opcode_info["Opcode Name"])
                            opcode_item.setTextAlignment(Qt.AlignCenter)
                            font = QFont()
                            font.setItalic(True)
                            opcode_item.setFont(font)
                        # Update description
                        description_item = self.table_widget.item(row, 2)
                        if description_item:
                            description_item.setText(selected_opcode_info["Opcode Description"])
                            description_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        # Handle Unknown opcode
                        opcode_item = self.table_widget.item(row, 0)
                        if opcode_item:
                            opcode_item.setText("Unknown")
                            opcode_item.setTextAlignment(Qt.AlignCenter)
                            font = QFont()
                            font.setItalic(True)
                            opcode_item.setFont(font)
                        description_item = self.table_widget.item(row, 2)
                        if description_item:
                            description_item.setText("")
                            description_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

if __name__ == "__main__":
    ensure_writable_json_files()
    app = QApplication(sys.argv)
    icon_path = resource_path("Blue.ico")
    app.setWindowIcon(QIcon(icon_path))  # Set the application icon
    window = SCDOpcodeHelper()
    window.show()
    logging.info("Application started.")
    sys.exit(app.exec_())
