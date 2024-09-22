import json
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QColorDialog, QGridLayout, QVBoxLayout, QWidget, QHBoxLayout,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class ThemeEditor(QDialog):
    def __init__(self, parent, theme_name, theme_style):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # Remove the question mark
        self.setWindowTitle("Theme Editor")
        self.theme_name = theme_name
        self.theme_style = theme_style.copy()
        self.new_theme_style = {}

        self.setStyleSheet(parent.styleSheet())

        # Apply palette
        palette = self.palette()
        main_window_style = parent.themes[parent.current_theme_name].get("QMainWindow", {})
        background_color = main_window_style.get("background-color", "")
        text_color = main_window_style.get("color", "")

        if background_color:
            palette.setColor(self.backgroundRole(), QColor(background_color))
        if text_color:
            palette.setColor(self.foregroundRole(), QColor(text_color))

        self.setPalette(palette)

        # Set fixed size
        self.setFixedSize(400, 500)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Grid layout for the theme properties
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # Theme Name
        name_label = QLabel("Theme Name:")
        self.name_field = QLineEdit(theme_name)
        grid_layout.addWidget(name_label, 0, 0, 1, 1)
        grid_layout.addWidget(self.name_field, 0, 1, 1, 2)

        # Iterate over the widgets and properties
        row = 1
        self.property_fields = []
        for widget_name, properties in theme_style.items():
            widget_label = QLabel(widget_name)
            widget_label.setStyleSheet("font-weight: bold;")
            grid_layout.addWidget(widget_label, row, 0, 1, 3)
            row += 1

            for prop_name, value in properties.items():
                prop_label = QLabel(prop_name)
                prop_field = QLineEdit(value)
                color_button = QPushButton("Choose Color")
                color_button.clicked.connect(lambda checked, field=prop_field: self.choose_color(field))

                grid_layout.addWidget(prop_label, row, 0)
                grid_layout.addWidget(prop_field, row, 1)
                grid_layout.addWidget(color_button, row, 2)

                self.property_fields.append((widget_name, prop_name, prop_field))
                row += 1

        # Add the grid layout to the main layout
        main_layout.addLayout(grid_layout)

        # Spacer before the save button
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Save Button (centered)
        save_button = QPushButton("Save Theme")
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        save_button.clicked.connect(self.accept)

    def choose_color(self, field):
        color_dialog = QColorDialog(self)
        color_dialog.setStyleSheet(self.styleSheet())
        if color_dialog.exec_():
            color = color_dialog.selectedColor()
            if color.isValid():
                field.setText(color.name())

    def get_new_theme(self):
        new_theme_name = self.name_field.text()
        new_theme_style = {}
        for widget_name, prop_name, prop_field in self.property_fields:
            if widget_name not in new_theme_style:
                new_theme_style[widget_name] = {}
            new_theme_style[widget_name][prop_name] = prop_field.text()
        return new_theme_name, new_theme_style
