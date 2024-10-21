from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

def move_row_up(window: QTableWidget):
    """Move the selected row up in the table."""
    selected_items = window.table_widget.selectedItems()
    if not selected_items:
        return  # No row is selected

    selected_row = selected_items[0].row()
    if selected_row == 0:
        return  # Already at the top row

    try:
        window.table_widget.blockSignals(True)

        # Swap the row data with the row above
        for column in range(window.table_widget.columnCount()):
            current_item = window.table_widget.takeItem(selected_row, column)
            above_item = window.table_widget.takeItem(selected_row - 1, column)

            window.table_widget.setItem(selected_row - 1, column, current_item)
            window.table_widget.setItem(selected_row, column, above_item)

        # Move the selection to the new position
        window.table_widget.selectRow(selected_row - 1)

    finally:
        window.table_widget.blockSignals(False)


def move_row_down(window: QTableWidget):
    """Move the selected row down in the table."""
    selected_items = window.table_widget.selectedItems()
    if not selected_items:
        return  # No row is selected

    selected_row = selected_items[0].row()
    if selected_row == window.table_widget.rowCount() - 1:
        return  # Already at the bottom row

    try:
        window.table_widget.blockSignals(True)

        # Swap the row data with the row below
        for column in range(window.table_widget.columnCount()):
            current_item = window.table_widget.takeItem(selected_row, column)
            below_item = window.table_widget.takeItem(selected_row + 1, column)

            window.table_widget.setItem(selected_row + 1, column, current_item)
            window.table_widget.setItem(selected_row, column, below_item)

        # Move the selection to the new position
        window.table_widget.selectRow(selected_row + 1)

    finally:
        window.table_widget.blockSignals(False)
