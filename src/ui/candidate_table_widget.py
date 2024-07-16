from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem, QWidget
from PySide6.QtCore import Qt, Slot, Signal


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        self.value = int(value)
        super().__init__(str(self.value))

    def __lt__(self, other):
        return self.value < other.value


class CandidateTableWidget(QWidget):
    trigger_focus_selection = Signal()

    def __init__(self):
        super().__init__()

        self.table_widget = QTableWidget()
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_widget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.verticalHeader().setVisible(False)

        self.sorting_orders = {}
        self.candidates = []
        self.best_candidates = {}
        self.open_coords_list = []
        self.played_tiles = {}
        self.reinit()

    def set_columns(self, columns):
        self.table_widget.setColumnCount(len(columns))
        for i, (header, tooltip, width) in enumerate(columns):
            item = QTableWidgetItem(header)
            item.setToolTip(tooltip)
            self.table_widget.setHorizontalHeaderItem(i, item)
            self.table_widget.setColumnWidth(i, width)
        self.sorting_orders = {c: Qt.AscendingOrder for c in range(self.table_widget.columnCount())}

    def reinit(self):
        self._clear_table()
        self.candidates = []
        self.best_candidates = {}
        self.open_coords_list = []
        self.played_tiles = {}

    @Slot()
    def handle_reset(self):
        self.reinit()

    @Slot(tuple)
    def handle_update_candidates(self, event):
        self.candidates, self.best_candidates, self.open_coords_list = event
        self._reset_scrollbars()

    @Slot(tuple)
    def handle_updated_session(self, session):
        self.candidates = []
        self.best_candidates = {}
        self.played_tiles = session.played_tiles
        self.open_coords_list = session.open_coords

    @Slot()
    def handle_manual_selection(self):
        self.trigger_focus_selection.emit()

    def _get_column_text_for_selected_row(self, column_index):
        selected_rows = list(
            {item.row() for item in self.table_widget.selectedItems()}
        )
        if len(selected_rows) == 1:
            item = self.table_widget.item(selected_rows[0], column_index)
            if item is not None:
                return item.text()

        return None

    def _select_row_if_column_text_matches(self, column_index, text):
        # if row is already selected -> return
        selected_text = self._get_column_text_for_selected_row(column_index)
        if selected_text == text:
            return True

        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, column_index)
            if item is not None and item.text() == text:
                self._select_row_without_emitting_signals(row)
                return True
        return False

    def _select_row_without_emitting_signals(self, row):
        # temporarily block signals in order not to trigger the itemSelectionChanged event
        self.table_widget.blockSignals(True)
        try:
            if row >= 0:
                self.table_widget.selectRow(row)
            else:
                self.table_widget.clearSelection()
        finally:
            self.table_widget.blockSignals(False)

    def _clear_table(self):
        # temporarily block signals in order not to trigger the itemSelectionChanged event
        self.table_widget.blockSignals(True)
        try:
            self.table_widget.clearSelection()
            self.table_widget.clearContents()
            self.table_widget.setRowCount(0)
        finally:
            self.table_widget.blockSignals(False)

    def _reset_scrollbars(self):
        self.table_widget.verticalScrollBar().setValue(0)
        self.table_widget.horizontalScrollBar().setValue(0)
