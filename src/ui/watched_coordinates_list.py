import ast

from PySide6.QtWidgets import (
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt, Slot, Signal

from src.constants import UIConstants

from src.ui.candidate_table_widget import CandidateTableWidget, NumericTableWidgetItem


class WatchedCoordinatesList(CandidateTableWidget):
    trigger_unwatch_coordinates = Signal(tuple)
    coordinates_selected = Signal(tuple)
    toggle_open_coords_display = Signal()
    trigger_clear_selection = Signal()

    def __init__(self):
        super().__init__()
        self.coords_col_idx = 2

        self.setFixedWidth(UIConstants.WATCHED_CANDIDATE_WIDTH)
        self.setup_ui()

        self.watch_candidate = None
        self.watched_open_coords_dict = {}

        self.table_widget.itemSelectionChanged.connect(self.handle_selection_changed)
        self.table_widget.cellClicked.connect(self.handle_selection_changed)
        # trigger through manual selection of a row entry in the table
        self.table_widget.itemSelectionChanged.connect(self.handle_manual_selection)
        self.table_widget.cellClicked.connect(self.handle_manual_selection)

    def setup_ui(self):
        layout = QVBoxLayout()

        candidates_label = QLabel("Watched coordinates:")
        layout.addWidget(candidates_label)

        columns = [
            ("CNo", "Candidate number", 50),
            ("Rating", "Candidate rating value", 55),
            ("Coords", "Watched coordinates", 60),
            ("Seen", "Num tiles seen that would match perfectly", 50),
        ]
        self.set_columns(columns)

        layout.addWidget(self.table_widget)

        button_layout = QHBoxLayout()
        self.watch_button = QPushButton("Watch")
        self.watch_button.setEnabled(False)
        button_layout.addWidget(self.watch_button)
        self.unwatch_button = QPushButton("Unwatch")
        self.unwatch_button.setEnabled(False)
        button_layout.addWidget(self.unwatch_button)
        self.toggle_display_button = QPushButton("Toggle")
        button_layout.addWidget(self.toggle_display_button)
        layout.addLayout(button_layout)

        self.unwatch_button.clicked.connect(self.handle_unwatch)
        self.toggle_display_button.clicked.connect(
            self.handle_toggle_open_coords_display
        )

        self.setLayout(layout)

    def handle_updated_session(self, session):
        super().handle_updated_session(session)
        self.watched_open_coords_dict = session.watched_open_coords
        self.update_table()
        self.set_buttons()

    def handle_update_candidates(self, event):
        super().handle_update_candidates(event)
        self.update_table()

    @Slot(tuple)
    def handle_update_watched_coords(self, event):
        self.watch_candidate = None
        watched_open_coords, coordinates, added = event
        self.watched_open_coords_dict = watched_open_coords
        self.update_table()

        if added:
            self.update_coords_selection(coordinates)
        else:
            self.trigger_clear_selection.emit()

    @Slot()
    def handle_toggle_open_coords_display(self):
        self.toggle_open_coords_display.emit()

    def reinit(self):
        super().reinit()
        self.watch_candidate = None
        self.watched_open_coords_dict = {}

    @Slot()
    def handle_reset(self):
        super().handle_reset()
        self.set_buttons()
        self.toggle_display_button.setEnabled(True)

    @Slot()
    def clear_selection(self):
        self.watch_candidate = None
        self.update_table()
        self.set_buttons()
        self._select_row_without_emitting_signals(-1)

    def set_buttons(self, watch=False, unwatch=False):
        self.watch_button.setEnabled(watch)
        self.unwatch_button.setEnabled(unwatch)

    @Slot()
    def handle_selection_changed(self):
        if (coords := self._get_selected_coordinates()) is not None:
            self.set_buttons(unwatch=True)
            self.coordinates_selected.emit(coords)
        else:
            self.set_buttons()
            self.clear_selection()

    @Slot()
    def handle_toggle(self):
        if self.toggle_display_button.isEnabled():
            self.handle_toggle_open_coords_display()

    @Slot(bool)
    def handle_unwatch(self, args):
        coords = self._get_selected_coordinates()
        if coords is not None:
            self.trigger_unwatch_coordinates.emit(coords)

    @Slot(tuple)
    def update_watch_candidate(self, watch_candidate):
        self.watch_candidate = watch_candidate

        self.update_table()

        if self.watch_candidate is not None:
            self.update_coords_selection(self.watch_candidate[0])

    def update_coords_selection(self, coords):
        if coords not in self.open_coords_list:
            self.trigger_clear_selection.emit()
            return

        if coords in self.watched_open_coords_dict:
            self._select_row_by_coordinates(coords)
            self.set_buttons(unwatch=True)
        else:
            self.set_buttons(watch=True)
            if self.watch_candidate is not None and coords == self.watch_candidate[0]:
                self._select_row_by_coordinates(coords)
            else:
                self._select_row_without_emitting_signals(-1)
        self.coordinates_selected.emit(coords)

    @Slot(bool)
    def set_toggle_open_coordinates_display_enabled(self, enabled):
        self.toggle_display_button.setEnabled(enabled)

    def update_table(self):
        self._clear_table()
        row_entries = {}

        def add_entry(coords, candidate_id, candidate_rating, num_seen):
            row_entries[coords] = [
                QTableWidgetItem(candidate_id),
                QTableWidgetItem(candidate_rating),
                NumericTableWidgetItem(num_seen),
            ]

        def get_index(index, is_watch_candidate=False):
            ret_val = (
                str(index + 1) if isinstance(index, int) else index
            )  # display 1-based
            return ret_val + " *" if is_watch_candidate else ret_val

        def get_rating(rating):
            return str(int(rating)) if isinstance(rating, (int, float)) else rating

        if self.candidates is not None and self.candidates:
            for idx, candidate in enumerate(self.candidates):
                if (
                    self.watch_candidate is not None
                    and candidate.tile.coordinates == self.watch_candidate[0]
                ):
                    if (coords := self.watch_candidate[0]) not in row_entries:
                        add_entry(
                            coords,
                            get_index(idx, True),
                            get_rating(candidate.rating),
                            self.watch_candidate[1],
                        )

                for coords in self.watched_open_coords_dict.keys():
                    if (
                        candidate.tile.coordinates == coords
                        and coords not in row_entries
                    ):
                        add_entry(
                            coords,
                            get_index(idx),
                            get_rating(candidate.rating),
                            self.watched_open_coords_dict[coords],
                        )
                        break

                # candidate list is ordered by rating, therefore once we have found the best
                # candidate for all watched coordinates and possibly watch candidate, we are done
                expected_length = len(self.watched_open_coords_dict) + int(
                    self.watch_candidate is not None
                )
                if len(row_entries) == expected_length:
                    break
        else:
            if (
                self.watch_candidate is not None
                and self.watch_candidate[0] not in self.watched_open_coords_dict
            ):
                add_entry(
                    self.watch_candidate[0],
                    get_index(UIConstants.NO_INDEX, True),
                    get_rating(UIConstants.NO_RATING),
                    self.watch_candidate[1],
                )

            for coords in self.watched_open_coords_dict.keys():
                add_entry(
                    coords,
                    get_index(UIConstants.NO_INDEX),
                    get_rating(UIConstants.NO_RATING),
                    self.watched_open_coords_dict[coords],
                )

        for row_index, (coords, (c_no, c_rating, c_seen)) in enumerate(
            row_entries.items()
        ):
            self.table_widget.insertRow(row_index)
            self.table_widget.setItem(row_index, 0, c_no)
            self.table_widget.setItem(row_index, 1, c_rating)
            self.table_widget.setItem(
                row_index, self.coords_col_idx, QTableWidgetItem(str(coords))
            )
            self.table_widget.setItem(row_index, 3, c_seen)

            # flag read-only after filling
            for col_index in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_index, col_index)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table_widget.repaint()

    def _get_selected_coordinates(self):
        if (
            coords := self._get_column_text_for_selected_row(self.coords_col_idx)
        ) is not None:
            return ast.literal_eval(coords)
        return None

    def _select_row_by_coordinates(self, coordinates):
        return self._select_row_if_column_text_matches(
            self.coords_col_idx, str(coordinates)
        )
