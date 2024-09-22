from PyQt5.QtWidgets import QAction, QStyle  # Import QStyle for standard icons
from PyQt5.QtGui import QIcon

def create_menu(window):
    menubar = window.menuBar()

    # File Menu
    file_menu = menubar.addMenu("File")
    exit_action = QAction(window.style().standardIcon(QStyle.SP_DialogCancelButton), "Exit", window)  # SP_DialogCancelButton icon
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    # Edit Menu
    edit_menu = menubar.addMenu("Edit")
    
    undo_action = QAction(window.style().standardIcon(QStyle.SP_ArrowLeft), "Undo", window)  # SP_ArrowLeft icon
    undo_action.triggered.connect(window.undo_hex_data)
    edit_menu.addAction(undo_action)

    redo_action = QAction(window.style().standardIcon(QStyle.SP_ArrowRight), "Redo", window)  # SP_ArrowRight icon
    redo_action.triggered.connect(window.redo_hex_data)
    edit_menu.addAction(redo_action)

    copy_action = QAction(window.style().standardIcon(QStyle.SP_FileDialogContentsView), "Copy", window)  # SP_FileDialogContentsView icon
    copy_action.triggered.connect(window.copy_hex_data)
    edit_menu.addAction(copy_action)

    paste_action = QAction(window.style().standardIcon(QStyle.SP_DialogOpenButton), "Paste", window)  # SP_DialogOpenButton icon for Paste
    paste_action.triggered.connect(window.paste_hex_data)
    edit_menu.addAction(paste_action)

    # Theme Menu
    theme_menu = menubar.addMenu("Theme")
    window.add_theme_menu(theme_menu)  # Icons are set within this method

    # Add "Edit Current Theme" action with SP_DialogNoButton icon
    edit_theme_action = QAction(window.style().standardIcon(QStyle.SP_DialogNoButton), "Edit Current Theme", window)
    edit_theme_action.triggered.connect(window.edit_current_theme)
    theme_menu.addAction(edit_theme_action)

    # Help Menu
    help_menu = menubar.addMenu("Help")
    
    instructions_action = QAction(window.style().standardIcon(QStyle.SP_MessageBoxQuestion), "Instructions", window)  # SP_MessageBoxQuestion icon
    instructions_action.triggered.connect(window.show_instructions)
    help_menu.addAction(instructions_action)

    about_action = QAction(window.style().standardIcon(QStyle.SP_DialogApplyButton), "About", window)  # SP_DialogApplyButton icon
    about_action.triggered.connect(window.show_about)
    help_menu.addAction(about_action)
