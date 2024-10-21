import sys
import os
import json
import shutil  # Added for file operations
from collections import OrderedDict
from PyQt5.QtWidgets import (
    QDialog, QComboBox, QLineEdit, QTextEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
    QGridLayout, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

def get_app_path(subdirectory=""):
    """Get the application path, accounting for PyInstaller's temporary directory."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        base_path = os.path.dirname(sys.executable)
    else:
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
    json_files = ["re1_opcodes.json", "re15_opcodes.json", "re2_opcodes.json", "re3_opcodes.json"]
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

def open_opcode_editor(window):
    ensure_writable_json_files()  # Ensure JSON files are available
    if not window.current_opcodes:
        print("No opcodes loaded.")
        return

    editor_dialog = QDialog(window)
    editor_dialog.setWindowFlags(editor_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    editor_dialog.setWindowTitle("Opcode Editor")
    editor_dialog.setFixedSize(600, 600)  # Set fixed size

    # Apply the current theme's stylesheet
    editor_dialog.setStyleSheet(window.styleSheet())

    # Apply palette
    palette = editor_dialog.palette()
    table_style = window.themes[window.current_theme_name].get("QTableWidget", {})
    background_color = table_style.get("background-color", "")
    text_color = table_style.get("color", "")

    if background_color:
        palette.setColor(editor_dialog.backgroundRole(), QColor(background_color))
    if text_color:
        palette.setColor(editor_dialog.foregroundRole(), QColor(text_color))

    editor_dialog.setPalette(palette)

    # Main vertical layout
    main_layout = QVBoxLayout(editor_dialog)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(10, 10, 10, 10)

    # Grid layout for the top section
    top_grid_layout = QGridLayout()
    top_grid_layout.setSpacing(10)

    # Row 0: SELECT OPCODE
    select_label = QLabel("SELECT OPCODE:")
    opcode_dropdown = QComboBox()

    # Create a flat list of opcode entries
    opcode_entries = []
    for opcode_number, key_opcode_info_list in window.current_opcodes.items():
        for key, opcode_info in key_opcode_info_list:
            opcode_entries.append((key, opcode_number, opcode_info))

    # Sort opcode entries by opcode number
    opcode_entries.sort(key=lambda x: int(x[1], 16))

    # Populate the opcode dropdown
    for index, (key, opcode_number, opcode_info) in enumerate(opcode_entries):
        opcode_dropdown.addItem(f"{opcode_number}: {opcode_info['Opcode Name']}")

    top_grid_layout.addWidget(select_label, 0, 0)
    top_grid_layout.addWidget(opcode_dropdown, 1, 0)

    # Row 1: OPCODE NAME
    name_label = QLabel("OPCODE NAME:")
    name_field = QLineEdit()
    top_grid_layout.addWidget(name_label, 0, 3)
    top_grid_layout.addWidget(name_field, 1, 3)

    # Row 2: OPCODE DESCRIPTION
    desc_label = QLabel("OPCODE DESCRIPTION:")
    description_field = QTextEdit()
    description_field.setFixedHeight(80)
    top_grid_layout.addWidget(desc_label, 4, 0)
    # Span the description_field across all columns (assuming 4 columns)
    top_grid_layout.addWidget(description_field, 5, 0, 1, 4)

    # Add the top grid layout to the main layout
    main_layout.addLayout(top_grid_layout)

    # Spacer between top section and table
    main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

    # Bytes Table
    bytes_table = QTableWidget()
    bytes_table.setColumnCount(4)
    bytes_table.setHorizontalHeaderLabels(["BYTE", "NAME", "TYPE", "DESCRIPTION"])
    bytes_table.horizontalHeader().setStretchLastSection(True)
    bytes_table.verticalHeader().setVisible(False)
    bytes_table.setEditTriggers(QTableWidget.AllEditTriggers)
    main_layout.addWidget(bytes_table)

    # Set column widths and resizing behavior
    bytes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # BYTE
    bytes_table.setColumnWidth(0, 60)  # Set fixed width for BYTE column

    bytes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)  # NAME
    bytes_table.setColumnWidth(1, 120)  # Set fixed width for NAME column

    bytes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)  # TYPE
    bytes_table.setColumnWidth(2, 80)  # Set fixed width for TYPE column

    bytes_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # DESCRIPTION takes remaining space

    # Disable manual resizing
    bytes_table.horizontalHeader().setSectionsMovable(False)
    bytes_table.horizontalHeader().setSectionsClickable(False)

    # Center align headers and make them bold with inverted colors
    header_font = QFont()
    header_font.setBold(True)
    bytes_table.horizontalHeader().setFont(header_font)
    bytes_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #000000; color: #ffffff; }")

    # Spacer between table and save button
    main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    # Save Button (centered)
    save_button = QPushButton("Save Changes")
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(save_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)

    # Track unsaved changes
    unsaved_changes = {'status': False}

    def set_unsaved_changes(status):
        unsaved_changes['status'] = status

    def has_unsaved_changes_func():
        return unsaved_changes['status']

    def update_fields():
        # Check for unsaved changes before switching opcodes
        if has_unsaved_changes_func():
            reply = QMessageBox.question(
                editor_dialog,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before switching opcodes?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                save_changes()
            elif reply == QMessageBox.Cancel:
                # Revert the dropdown selection to previous index
                opcode_dropdown.blockSignals(True)
                opcode_dropdown.setCurrentIndex(update_fields.previous_index)
                opcode_dropdown.blockSignals(False)
                return
            else:
                # Discard changes
                set_unsaved_changes(False)

        update_fields.previous_index = opcode_dropdown.currentIndex()

        # Clear existing rows
        bytes_table.setRowCount(0)

        selected_index = opcode_dropdown.currentIndex()
        if selected_index >= 0 and selected_index < len(opcode_entries):
            key, opcode_number, selected_opcode = opcode_entries[selected_index]
            name_field.setText(selected_opcode.get("Opcode Name", ""))
            description_field.setText(selected_opcode.get("Opcode Description", ""))

            # Add byte details to the table
            if "Bytes" in selected_opcode:
                current_byte = 1
                for byte_name, byte_info in selected_opcode["Bytes"].items():
                    byte_type = byte_info.get("Type", "")
                    byte_desc = byte_info.get("Description", "")

                    # Calculate byte range
                    if byte_type in ["UCHAR", "CHAR"]:
                        byte_range = f"{current_byte:02d}"
                        current_byte += 1
                    else:
                        byte_range = f"{current_byte:02d}-{current_byte + 1:02d}"
                        current_byte += 2

                    row = bytes_table.rowCount()
                    bytes_table.insertRow(row)

                    # Byte range
                    byte_item = QTableWidgetItem(byte_range)
                    byte_item.setFlags(byte_item.flags() & ~Qt.ItemIsEditable)
                    byte_item.setTextAlignment(Qt.AlignCenter)
                    bytes_table.setItem(row, 0, byte_item)

                    # Name
                    name_item = QTableWidgetItem(byte_name)
                    name_item.setTextAlignment(Qt.AlignCenter)
                    if row == 0:
                        # Make the Name cell non-editable for Byte 1
                        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    else:
                        name_item.setForeground(QColor("#000000"))  # Set black text for editable cells
                        name_item.setBackground(QColor("#E0E0E0"))  # Set background for visibility
                    bytes_table.setItem(row, 1, name_item)

                    # Type (dropdown)
                    type_dropdown = QComboBox()
                    type_dropdown.addItems(["UCHAR", "CHAR", "USHORT", "SHORT", "ULONG", "LONG"])
                    type_dropdown.setCurrentText(byte_type)
                    type_dropdown.setEnabled(row != 0)  # Disable editing for Byte 1
                    bytes_table.setCellWidget(row, 2, type_dropdown)
                    # Connect signal to track changes
                    type_dropdown.currentIndexChanged.connect(lambda: set_unsaved_changes(True))

                    # Description
                    desc_item = QTableWidgetItem(byte_desc)
                    desc_item.setTextAlignment(Qt.AlignCenter)
                    if row == 0:
                        # Make the Description cell non-editable for Byte 1
                        desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                    else:
                        desc_item.setForeground(QColor("#000000"))  # Set black text for editable cells
                        desc_item.setBackground(QColor("#E0E0E0"))  # Set background for visibility
                    bytes_table.setItem(row, 3, desc_item)

        # Reset unsaved changes status
        set_unsaved_changes(False)

    update_fields.previous_index = opcode_dropdown.currentIndex()
    opcode_dropdown.currentIndexChanged.connect(update_fields)
    update_fields()

    # Connect signals to track changes
    name_field.textChanged.connect(lambda: set_unsaved_changes(True))
    description_field.textChanged.connect(lambda: set_unsaved_changes(True))
    bytes_table.itemChanged.connect(lambda item: set_unsaved_changes(True))

    def save_changes():
        selected_index = opcode_dropdown.currentIndex()
        if selected_index >= 0 and selected_index < len(opcode_entries):
            key, opcode_number, selected_opcode = opcode_entries[selected_index]
            updated_opcode = selected_opcode.copy()  # Copy original opcode to preserve fields

            # Update fields from the editor
            updated_opcode["Opcode Name"] = name_field.text()
            updated_opcode["Opcode Description"] = description_field.toPlainText()

            # Save changes to byte fields
            updated_bytes = OrderedDict()
            for i in range(bytes_table.rowCount()):
                byte_name = bytes_table.item(i, 1).text()
                byte_widget = bytes_table.cellWidget(i, 2)
                byte_type = byte_widget.currentText() if isinstance(byte_widget, QComboBox) else ""
                byte_desc = bytes_table.item(i, 3).text()
                updated_bytes[byte_name] = {
                    "Type": byte_type,
                    "Description": byte_desc
                }
            updated_opcode["Bytes"] = updated_bytes

            # Save the updated data to file without altering formatting
            game = window.dropdown.currentText()
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
                try:
                    # Read the original file lines
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    # Find the opcode block in the lines
                    start_index = None
                    end_index = None
                    brace_count = 0
                    opcode_key_line = f'"{key}":'
                    for i, line in enumerate(lines):
                        if opcode_key_line in line:
                            start_index = i
                            brace_count = line.count('{') - line.count('}')
                            break

                    if start_index is None:
                        raise Exception(f"Opcode {key} not found in {file_name}.")

                    # Find the end of the opcode block
                    for i in range(start_index + 1, len(lines)):
                        brace_count += lines[i].count('{') - lines[i].count('}')
                        if brace_count == 0:
                            end_index = i
                            break

                    if end_index is None:
                        raise Exception(f"Could not determine the end of opcode {key} in {file_name}.")

                    # Extract the opcode block
                    opcode_block_lines = lines[start_index:end_index + 1]

                    # Build a mapping from field names to their line indices
                    field_indices = {}
                    for idx, line in enumerate(opcode_block_lines):
                        stripped_line = line.strip()
                        if stripped_line.startswith('"'):
                            parts = stripped_line.split('"')
                            if len(parts) > 2:
                                field_name = parts[1]
                                field_indices[field_name] = idx

                    # Update the fields in opcode_block_lines
                    def update_field(field_name, new_value):
                        idx = field_indices.get(field_name)
                        if idx is not None:
                            line = opcode_block_lines[idx]
                            # Preserve any existing commas
                            if line.strip().endswith(','):
                                comma = ','
                            else:
                                comma = ''
                            # Reconstruct the line
                            prefix = line.split(':')[0]
                            opcode_block_lines[idx] = f'{prefix}: "{new_value}"{comma}\n'

                    # Update all fields present in the original opcode
                    for field_name, value in updated_opcode.items():
                        if field_name != "Bytes":
                            update_field(field_name, value)

                    # Update Bytes section
                    bytes_start = field_indices.get("Bytes")
                    if bytes_start is not None:
                        # Find the start and end of the Bytes block
                        brace_count = opcode_block_lines[bytes_start].count('{') - opcode_block_lines[bytes_start].count('}')
                        bytes_end = None
                        for i in range(bytes_start + 1, len(opcode_block_lines)):
                            brace_count += opcode_block_lines[i].count('{') - opcode_block_lines[i].count('}')
                            if brace_count == 0:
                                bytes_end = i
                                break
                        if bytes_end is None:
                            raise Exception(f"Could not determine the end of 'Bytes' section in opcode {key}.")

                        # Reconstruct the Bytes section
                        indent = opcode_block_lines[bytes_start].split('"Bytes":')[0]
                        new_bytes_lines = [opcode_block_lines[bytes_start]]  # Keep the '"Bytes": {' line as is

                        byte_items = list(updated_opcode["Bytes"].items())
                        for idx, (byte_name, byte_info) in enumerate(byte_items):
                            new_bytes_lines.append(indent + f'    "{byte_name}": {{\n')
                            new_bytes_lines.append(indent + f'        "Type": "{byte_info["Type"]}",\n')
                            new_bytes_lines.append(indent + f'        "Description": "{byte_info["Description"]}"\n')
                            if idx < len(byte_items) - 1:
                                new_bytes_lines.append(indent + f'    }},\n')
                            else:
                                new_bytes_lines.append(indent + f'    }}\n')
                        # Check if the original Bytes section had a trailing comma
                        if opcode_block_lines[bytes_end].strip().endswith(','):
                            new_bytes_lines.append(indent + '},\n')  # Closing brace for Bytes section with comma
                        else:
                            new_bytes_lines.append(indent + '}\n')  # Closing brace for Bytes section

                        # Replace the old Bytes section with the new one
                        opcode_block_lines = opcode_block_lines[:bytes_start] + new_bytes_lines + opcode_block_lines[bytes_end + 1:]
                    else:
                        raise Exception(f"'Bytes' section not found in opcode {key}.")

                    # Replace the old opcode block in lines
                    lines = lines[:start_index] + opcode_block_lines + lines[end_index + 1:]

                    # Write back to the file
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)

                    print(f"Opcode data saved to {full_path}")

                    # Reload the opcodes
                    window.current_opcodes = window.load_opcode_data(game)
                    window.hex_delegate.original_hex_values = window.original_hex_values  # Update original_hex_values
                    # Update the opcode keys for auto-completion
                    opcode_keys = []
                    for opcode_list in window.current_opcodes.values():
                        for _, opcode_info in opcode_list:
                            opcode_keys.append(opcode_info["Opcode Name"])
                    window.hex_delegate.opcode_keys = opcode_keys

                    # Reset unsaved changes status
                    set_unsaved_changes(False)

                    # Display success message with theme styling
                    msg_box = QMessageBox(editor_dialog)
                    msg_box.setIcon(QMessageBox.Information)
                    msg_box.setWindowTitle("Success")
                    msg_box.setText(f"Opcode data saved to {full_path}")
                    msg_box.setStyleSheet(window.styleSheet())
                    window.apply_palette_to_widget(msg_box)
                    msg_box.exec_()

                except Exception as e:
                    print(f"Error saving opcode data: {e}")
                    # Show error message with current theme
                    msg_box = QMessageBox(editor_dialog)
                    msg_box.setIcon(QMessageBox.Critical)
                    msg_box.setWindowTitle("Error")
                    msg_box.setText(f"Failed to save opcode data: {e}")
                    msg_box.setStyleSheet(window.styleSheet())
                    window.apply_palette_to_widget(msg_box)
                    msg_box.exec_()

    save_button.clicked.connect(save_changes)

    editor_dialog.exec_()
