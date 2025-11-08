from PySide6.QtWidgets import QTableWidgetItem, QVBoxLayout
from PySide6.QtCore import Qt, Slot, Signal

from src.side import Side
from src.ui.constants import UIConstants

from src.ui.candidate_table_widget import CandidateTableWidget, NumericTableWidgetItem


class CandidateList(CandidateTableWidget):
    candidate_selection_changed = Signal(int)
    selection_confirmed = Signal(tuple)

    def __init__(self):
        super().__init__()
        self.index_col_idx = 0
        self.index_col_rating = 4

        self.setFixedWidth(UIConstants.CANDIDATE_LIST_WIDTH)
        self.setup_ui()

        self.table_widget.itemSelectionChanged.connect(self.handle_selection_changed)
        self.table_widget.cellClicked.connect(self.handle_selection_changed)
        # trigger through manual selection of a row entry in the table
        self.table_widget.itemSelectionChanged.connect(self.handle_manual_selection)
        self.table_widget.cellClicked.connect(self.handle_manual_selection)

    def setup_ui(self):
        layout = QVBoxLayout()

        columns = [
            ("No", "Candidate number", 15),
            ("Perf", "Perfect side placement count", 50),
            ("Imperf", "Imperfect side placement count", 50),
            ("PClosed", "Perfectly closed tiles count", 60),
            ("Rating", "Candidate rating value", 60),
            ("Placement", "Tile placement rating", 70),
            ("Group size", "Group size rating", 70),
            ("Gr Interf.", "Neighbor group interference", 70),
            ("Neighbors", "Neighbor compatibility rating", 70),
            ("Types", "Neighbor type demotion rating", 60),
            ("ROrientation", "Restricted type orientation", 75),
            ("Coords", "Candidate coordinates", 60),
        ]
        self.set_columns(columns)

        self.table_widget.horizontalHeader().sectionClicked.connect(self.sort_table)

        layout.addWidget(self.table_widget)

        self.setLayout(layout)

    def handle_update_candidates(self, event):
        super().handle_update_candidates(event)
        self.update_table()

    def handle_updated_session(self, session):
        super().handle_updated_session(session)
        self.update_table()

    @Slot(tuple)
    def handle_rotated_candidate(self, rotated_candidate):
        for i, candidate in enumerate(self.candidates):
            # compare based on coordinates and sequence
            if (
                candidate.tile.coordinates == rotated_candidate.coordinates
                and candidate.tile.get_side_type_seq()
                == rotated_candidate.get_side_type_seq()
            ):
                self._select_row_by_candidate_index(i)
                return

    @Slot()
    def handle_selection_changed(self):
        if (index := self._get_selected_candidate_index()) >= 0:
            self.candidate_selection_changed.emit(index)

    @Slot()
    def confirm_selection(self):
        index = self._get_selected_candidate_index()
        if index < 0 or index >= len(self.candidates):
            return

        self.selection_confirmed.emit(self.candidates[index].tile)

    @Slot(int)
    def update_candidate_selection(self, index):
        if index < 0 or index >= len(self.candidates):
            return
        self._select_row_by_candidate_index(index)

    @Slot(int)
    def sort_table(self, index):
        current_order = self.sorting_orders[index]

        horizontal_scrollbar_value = self.table_widget.horizontalScrollBar().value()

        # Toggle sorting order (ascending <-> descending)
        new_order = (
            Qt.DescendingOrder
            if current_order == Qt.AscendingOrder
            else Qt.AscendingOrder
        )
        self.sorting_orders[index] = new_order

        self.table_widget.sortItems(index, new_order)

        # Scroll to ensure that a selected row remains visible
        if selected_items := self.table_widget.selectedItems():
            self.table_widget.scrollToItem(selected_items[0])

        # Restore the horizontal scrollbar value
        self.table_widget.horizontalScrollBar().setValue(horizontal_scrollbar_value)

    @Slot()
    def reset_best_selection_display(self):
        # * reset the scroll bars
        # * reset sorting to sort descending by rating
        # * select the highest rated candidate (first row)
        self.sorting_orders[self.index_col_rating] = (
            Qt.AscendingOrder
        )  # set ascending as sorting will toggle
        self.sort_table(self.index_col_rating)
        self._reset_scrollbars()

        if self.table_widget.rowCount() > 0:
            self._select_row_by_candidate_index(0)
            self.trigger_focus_selection.emit()

    def update_table(self):
        self._clear_table()
        for row_index, candidate in enumerate(self.candidates):
            self.table_widget.insertRow(row_index)

            self.table_widget.setItem(
                row_index, self.index_col_idx, NumericTableWidgetItem(row_index + 1)
            )  # display 1-based
            self.table_widget.setItem(
                row_index,
                1,
                NumericTableWidgetItem(
                    candidate.tile.get_num_sides(Side.Placement.PERFECT_MATCH)
                ),
            )
            self.table_widget.setItem(
                row_index,
                2,
                NumericTableWidgetItem(
                    candidate.tile.get_num_sides(Side.Placement.IMPERFECT_MATCH)
                ),
            )
            self.table_widget.setItem(
                row_index,
                3,
                NumericTableWidgetItem(
                    candidate.tile.get_num_perfectly_closed(self.played_tiles)
                ),
            )
            self.table_widget.setItem(
                row_index,
                self.index_col_rating,
                NumericTableWidgetItem(candidate.rating),
            )
            self.table_widget.setItem(
                row_index,
                5,
                NumericTableWidgetItem(candidate.rating_detail.tile_placement_rating),
            )
            self.table_widget.setItem(
                row_index,
                6,
                NumericTableWidgetItem(candidate.rating_detail.group_rating),
            )
            self.table_widget.setItem(
                row_index,
                7,
                NumericTableWidgetItem(
                    candidate.rating_detail.neighbor_group_interference_rating
                ),
            )
            self.table_widget.setItem(
                row_index,
                8,
                NumericTableWidgetItem(
                    candidate.rating_detail.neighbor_compatibility_rating
                ),
            )
            self.table_widget.setItem(
                row_index,
                9,
                NumericTableWidgetItem(
                    candidate.rating_detail.neighbor_type_demotion_rating
                ),
            )
            self.table_widget.setItem(
                row_index,
                10,
                NumericTableWidgetItem(
                    candidate.rating_detail.restricted_type_orientation_rating
                ),
            )
            self.table_widget.setItem(
                row_index, 11, QTableWidgetItem(str(candidate.tile.coordinates))
            )

            # flag read-only after filling
            for col_index in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_index, col_index)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        # automatically select first row to trigger display update
        if self.table_widget.rowCount() > 0:
            self._select_row_by_candidate_index(0)

    def _get_selected_candidate_index(self):
        if (
            idx_text := self._get_column_text_for_selected_row(self.index_col_idx)
        ) is not None and idx_text.isdigit():
            if (idx := int(idx_text)) > 0:
                return idx - 1  # display is 1-based, index is 0-based

        return -1

    def _select_row_by_candidate_index(self, index):
        if index < 0 or index >= len(self.candidates):
            return False

        # index display is 1-based
        if self._select_row_if_column_text_matches(self.index_col_idx, str(index + 1)):
            self.handle_selection_changed()
            return True

        return False
