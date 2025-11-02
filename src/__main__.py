import sys
import pandas as pd

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QFrame,
    QInputDialog,
    QDialog,
    QFileDialog,
    QRadioButton,
    QLabel,
)
from PySide6.QtGui import QAction, QFont
from PySide6.QtCore import Qt, Slot, Signal

from src.session import Session
from src.side_type import SideType, SIDE_TYPE_TO_CHAR
from src.tile import Tile
from src.constants import DatabaseConstants, UIConstants

from src.ui.tile_map_view import CandidateNeighborMapView, TileMapView
from src.ui.control_panel import ControlPanel
from src.ui.candidate_list import CandidateList
from src.ui.watched_coordinates_list import WatchedCoordinatesList
from src.ui.legend import Legend


class MainWidget(QMainWindow):
    start_session = Signal()
    trigger_save_session = Signal(str)
    trigger_save_to_csv = Signal(str)
    trigger_delete_session = Signal(int)
    trigger_load_session = Signal(tuple)
    trigger_load_from_csv = Signal(str)
    trigger_reset_session = Signal()
    trigger_next_tile = Signal(tuple)
    trigger_update_map = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(UIConstants.TITLE)
        self.setGeometry(200, 200, 1200, 900)
        self.session = Session(DatabaseConstants.DB_NAME)

        # tile by tile placement, triggered through loading a session
        self.tile_by_tile_data = None
        self.tile_by_tile_index = -1

        self.setup_ui()
        self.start_session.emit()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tile_map = TileMapView(UIConstants.Layer.LANDSCAPES)
        main_layout.addWidget(self.tile_map)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: dimGray;")

        main_layout.addWidget(separator)

        bottom_layout = QHBoxLayout()
        self.control_panel = ControlPanel(self.session)
        bottom_layout.addWidget(self.control_panel)
        self.candidate_list = CandidateList()
        bottom_layout.addWidget(self.candidate_list)
        self.candidate_neighbor_map = CandidateNeighborMapView()
        bottom_layout.addWidget(self.candidate_neighbor_map)
        self.watched_candidate_list = WatchedCoordinatesList()
        bottom_layout.addWidget(self.watched_candidate_list)
        bottom_layout.addWidget(Legend())

        main_layout.addLayout(bottom_layout)

        # Add menu bar
        new_action = QAction("&New Session", self)
        save_action = QAction("&Save Session", self)
        save_csv_action = QAction("&Save as CSV", self)
        load_action = QAction("&Load Session", self)
        load_csv_action = QAction("&Load from CSV", self)
        delete_action = QAction("&Delete Session", self)

        exit_action = QAction("&Exit", self)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        # Add actions to file menu
        file_menu.addAction(new_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_csv_action)
        file_menu.addAction(load_action)
        file_menu.addAction(load_csv_action)
        file_menu.addAction(delete_action)
        file_menu.addAction(exit_action)

        # Glue UI to business logic
        # file dialog
        new_action.triggered.connect(self.confirm_new)
        exit_action.triggered.connect(self.confirm_exit)
        load_action.triggered.connect(
            lambda: self.session.handle_get_all_sessions_from_database("load")
        )
        delete_action.triggered.connect(
            lambda: self.session.handle_get_all_sessions_from_database("delete")
        )
        load_csv_action.triggered.connect(self.load_session_from_csv)
        save_action.triggered.connect(self.save_session)
        save_csv_action.triggered.connect(self.save_session_to_csv)

        # session signals
        self.session.session_updated.connect(
            self.candidate_neighbor_map.handle_updated_session
        )
        self.session.session_updated.connect(self.tile_map.handle_updated_session)
        self.session.session_updated.connect(self.candidate_list.handle_updated_session)
        self.session.session_updated.connect(
            self.watched_candidate_list.handle_updated_session
        )
        self.session.session_updated.connect(self.control_panel.reset)
        self.session.session_updated.connect(
            lambda: self.control_panel.set_undo_button_enabled(True)
        )
        self.session.session_updated.connect(
            lambda: self.control_panel.set_place_button_enabled(False)
        )
        self.session.session_updated.connect(
            lambda: self.watched_candidate_list.set_toggle_open_coordinates_display_enabled(
                True
            )
        )
        self.session.session_updated.connect(self.control_panel.focus_next_sequence)
        self.session.session_updated.connect(self.fill_tile_by_tile)
        self.session.session_loaded.connect(self.tile_map.refresh)
        self.session.session_loaded.connect(
            self.tile_map.handle_toggle_open_coords_display
        )
        self.session.tile_placed.connect(self.tile_map.handle_placed_tile)
        self.session.tile_placed.connect(self.candidate_neighbor_map.refresh)
        self.session.tile_undone.connect(self.tile_map.handle_undone_tile)
        self.session.tile_undone.connect(self.candidate_neighbor_map.refresh)
        self.session.undone_tile_properties.connect(
            self.control_panel.prefill_next_tile
        )
        self.session.trigger_message_display.connect(self.show_message)
        self.session.trigger_display_help.connect(self.show_help)
        self.session.candidate_tiles_computed.connect(
            self.tile_map.handle_update_candidates
        )
        self.session.candidate_tiles_computed.connect(
            self.candidate_neighbor_map.handle_update_candidates
        )
        self.session.candidate_tiles_computed.connect(
            self.watched_candidate_list.handle_update_candidates
        )
        self.session.candidate_tiles_computed.connect(
            self.candidate_list.handle_update_candidates
        )
        self.session.candidate_tiles_computed.connect(
            lambda: self.control_panel.set_place_button_enabled(True)
        )
        self.session.candidate_tiles_computed.connect(
            self.control_panel.focus_place_button
        )
        self.session.candidate_tiles_computed.connect(
            self.tile_map.center_at_current_selection
        )
        self.session.similar_tiles_seen.connect(
            self.control_panel.update_similar_tiles_seen
        )
        self.session.candidate_rotated.connect(
            self.candidate_list.handle_rotated_candidate
        )
        self.session.session_reset.connect(self.candidate_neighbor_map.reset)
        self.session.session_reset.connect(self.tile_map.reset)
        self.session.session_reset.connect(self.candidate_list.handle_reset)
        self.session.session_reset.connect(self.watched_candidate_list.handle_reset)
        self.session.session_reset.connect(self.control_panel.reset)
        self.session.session_reset.connect(self.reset_tile_by_tile)
        self.session.sessions_loaded_from_database.connect(self.initiate_session_load)
        self.session.dataframe_loaded.connect(self.fill_tile_by_tile)
        self.session.watched_coordinates_changed.connect(
            self.watched_candidate_list.handle_update_watched_coords
        )
        self.session.watched_coordinates_changed.connect(
            self.tile_map.handle_watched_coordinates_changed
        )
        self.session.coordinates_selected.connect(
            self.watched_candidate_list.update_watch_candidate
        )

        # candidate list signals
        self.candidate_list.candidate_selection_changed.connect(
            self.tile_map.handle_update_candidate_selection
        )
        self.candidate_list.candidate_selection_changed.connect(
            self.candidate_neighbor_map.handle_update_candidate_selection
        )
        self.candidate_list.trigger_focus_selection.connect(
            self.tile_map.center_at_current_selection
        )
        self.candidate_list.selection_confirmed.connect(
            self.session.handle_place_candidate
        )

        # watched candidate list signals
        self.watched_candidate_list.watch_button.clicked.connect(
            self.tile_map.handle_watch_open_coordinates
        )
        self.watched_candidate_list.coordinates_selected.connect(
            self.tile_map.handle_update_coordinates_selection
        )
        self.watched_candidate_list.trigger_focus_selection.connect(
            self.tile_map.center_at_current_selection
        )
        self.watched_candidate_list.trigger_clear_selection.connect(
            self.tile_map.clear_coordinates_selection
        )
        self.watched_candidate_list.trigger_unwatch_coordinates.connect(
            self.session.handle_unwatch
        )
        self.watched_candidate_list.toggle_open_coords_display.connect(
            self.tile_map.handle_toggle_open_coords_display
        )

        # tile map signals
        self.tile_map.trigger_rotation.connect(self.session.handle_rotate_candidate)
        self.tile_map.candidate_selected.connect(
            self.candidate_list.update_candidate_selection
        )
        self.tile_map.coordinates_selected.connect(self.session.update_coords_selection)
        self.tile_map.coordinates_selected.connect(
            self.watched_candidate_list.update_coords_selection
        )
        self.tile_map.trigger_toggle_open_coords_display.connect(
            self.watched_candidate_list.handle_toggle
        )
        self.tile_map.trigger_watch_coordinates.connect(self.session.handle_watch)
        self.tile_map.trigger_unwatch_coordinates.connect(self.session.handle_unwatch)
        self.tile_map.trigger_clear_coordinates_selection.connect(
            self.watched_candidate_list.clear_selection
        )
        self.tile_map.confirm_selected_candidate.connect(
            self.candidate_list.confirm_selection
        )
        self.tile_map.trigger_toggle_map_display.connect(self.handle_toggle_display)

        # candidate neighbor map signals
        self.candidate_neighbor_map.trigger_rotation.connect(
            self.session.handle_rotate_candidate
        )

        # control panel signals
        self.control_panel.next_tile_sequence.focus_received.connect(
            self.tile_map.clear_coordinates_selection
        )
        self.control_panel.next_tile_sequence.focus_received.connect(
            self.watched_candidate_list.clear_selection
        )
        self.control_panel.next_tile_center.focus_received.connect(
            self.tile_map.clear_coordinates_selection
        )
        self.control_panel.next_tile_center.focus_received.connect(
            self.watched_candidate_list.clear_selection
        )
        self.control_panel.compute_button_clicked.connect(
            self.session.handle_compute_candidates
        )
        self.control_panel.compute_button_clicked.connect(
            lambda: self.watched_candidate_list.set_toggle_open_coordinates_display_enabled(
                False
            )
        )
        self.control_panel.compute_button_repeated.connect(
            self.candidate_list.reset_best_selection_display
        )
        self.control_panel.place_button.clicked.connect(
            self.candidate_list.confirm_selection
        )
        self.control_panel.undo_button.clicked.connect(
            self.session.handle_undo_last_tile
        )
        self.control_panel.trigger_message_display.connect(self.show_message)
        self.control_panel.trigger_display_help.connect(self.show_help)
        self.control_panel.trigger_display_stats.connect(self.show_stats)
        self.control_panel.toggle_map_display.connect(self.handle_toggle_display)

        # main window signals
        self.start_session.connect(self.session.handle_reset_session)
        self.start_session.connect(self.session.handle_start_session)
        self.start_session.connect(
            lambda: self.control_panel.set_undo_button_enabled(False)
        )
        self.trigger_save_session.connect(self.session.handle_save_session_to_database)
        self.trigger_save_to_csv.connect(self.session.handle_save_session_to_csv)
        self.trigger_load_session.connect(
            self.session.handle_load_session_from_database
        )
        self.trigger_load_session.connect(
            lambda: self.control_panel.set_undo_button_enabled(False)
        )
        self.trigger_load_from_csv.connect(self.session.handle_load_session_from_csv)
        self.trigger_load_from_csv.connect(
            lambda: self.control_panel.set_undo_button_enabled(False)
        )
        self.trigger_delete_session.connect(
            self.session.handle_delete_session_from_database
        )
        self.trigger_reset_session.connect(self.session.handle_reset_session)
        self.trigger_next_tile.connect(self.control_panel.prefill_next_tile)
        self.trigger_update_map.connect(self.tile_map.refresh)

    @Slot(tuple)
    def show_message(self, args):
        title, msg = args
        if len(title) > 0 and len(msg) > 0:
            message_box = QMessageBox()
            message_box.setText(msg)
            message_box.setWindowTitle(title)

            monospaced_font = QFont("Courier New")
            message_box.setFont(monospaced_font)
            message_box.exec()

    @Slot()
    def show_help(self):
        example_seq = "".join(
            [
                SIDE_TYPE_TO_CHAR[SideType.WOODS],
                SIDE_TYPE_TO_CHAR[SideType.HOUSE],
                SIDE_TYPE_TO_CHAR[SideType.WOODS],
                SIDE_TYPE_TO_CHAR[SideType.CROPS],
                SIDE_TYPE_TO_CHAR[SideType.WOODS],
                SIDE_TYPE_TO_CHAR[SideType.GREEN],
            ]
        )
        example_isolated_seq = (
            example_seq[:4] + "(" + example_seq[4] + ")" + example_seq[5:]
        )
        info_message = (
            "Specify the next tile in the "
            + f'"{UIConstants.NEXT_TILE_TITLE}" box in the lower left of the window.\n\n'
            + f'"{UIConstants.NEXT_TILE_SIDE_SEQ_TITLE}": Expecting either\n'
            + " - six characters, one for each side types OR\n"
            + "   (please note that you may use paranthesis\n"
            + "    to isolate a single side type from the center, see below)\n"
            + " - a single character for all side types and center.\n"
            + "   (in this case,\n"
            + "    it is not necessary to specify the center type )\n\n"
            + f'"{UIConstants.NEXT_TILE_CENTER_TITLE}": Expecting\n'
            + " - a single character for the center type\n\n"
            + "If there is a side that should be isolated from the center, "
            + "specify it in parenthesis. This will ensure that there is no connection from "
            + "the given side to any other sides of the same type through the center.\n\n"
            + "Side type characters may be specified in both, "
            + "upper and lower case\n\n"
            + "Examples:\n"
            + example_seq
            + "\n"
            + example_isolated_seq.lower()
            + "\n"
            + example_seq[0]
            + "\n"
            + "Valid landscape side type values:\n"
            + SideType.to_string()
            + "\n"
            + "You may also find the available types in the legend "
            + "in the bottom right corner of the window."
        )
        self.show_message(("Help", info_message))

    @Slot()
    def show_stats(self):
        count_marked_for_deletion = 0
        for groups in self.session.groups_marked_for_deletion_at_coords.values():
            count_marked_for_deletion += len(groups)

        info_message = (
            f"Score (without quests): {self.session.score}\n\n"
            f"Tiles placed: {len(self.session.played_tiles)}\n\n"
            f"Tiles closed: {self.session.get_closed_count()}\n"
            f" -> Perfect placements: {self.session.get_perfect_placement_count()} "
            f"({self.session.get_perfect_placement_percentage()} %)\n"
            f" -> Imperfect placements: {self.session.get_imperfect_placement_count()}\n\n"
            f"Tiles open: {self.session.get_open_count()}\n"
             " -> Perfect placements: "
            f"{self.session.get_open_placement_count(Tile.Placement.PERFECT)}\n"
             " -> Imperfect placements: "
            f"{self.session.get_open_placement_count(Tile.Placement.IMPERFECT)}\n\n"
            f"Groups: {len(self.session.groups)} "
            f"({count_marked_for_deletion} marked for deletion)\n"
        )
        self.show_message(("Game Statistics", info_message))

    @Slot()
    def handle_toggle_display(self):
        curr_idx = UIConstants.Layer.get_index(self.tile_map.layer_selection)
        self.tile_map.layer_selection = UIConstants.Layer.at_index(curr_idx + 1)
        self.trigger_update_map.emit()

    @Slot()
    def confirm_new(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm New")
        msg_box.setText("Are you sure you want to start a new session?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        result = msg_box.exec()
        if result == QMessageBox.Yes:
            self.start_session.emit()

    @Slot()
    def confirm_exit(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Exit")
        msg_box.setText("Are you sure you want to exit?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        result = msg_box.exec()
        if result == QMessageBox.Yes:
            self.close()

    @Slot()
    def load_session_from_csv(self):
        # Open file dialog for loading session
        file_path, _ = QFileDialog.getOpenFileName(self, "Load from CSV", "", "(*.csv)")
        if file_path:
            self.trigger_reset_session.emit()
            self.trigger_load_from_csv.emit(file_path)

    @Slot()
    def save_session(self):
        session_name, ok = QInputDialog.getText(
            self, "Save Session", "Enter session name:"
        )
        if ok and session_name:
            self.trigger_save_session.emit(session_name)

    @Slot()
    def save_session_to_csv(self):
        # Open file dialog for saving session
        file_path, _ = QFileDialog.getSaveFileName(self, "Save as CSV", "", "(*.csv)")
        if file_path:
            self.trigger_save_to_csv.emit(file_path)

    @Slot(tuple)
    def initiate_session_load(self, args):
        sessions, origin = args
        if sessions is None or sessions.empty:
            self.show_message(("Error", "Database does not yet contain any sessions"))
            return

        if origin not in ["load", "delete"]:
            raise ValueError("Invalid value")

        # Create a dialog to display sessions and options
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Session" if origin == "load" else "Delete Session")
        dialog.setMinimumSize(600, 300)
        layout = QVBoxLayout()

        table_widget = QTableWidget()
        column_titles = ["Name", "Save date", "Number of tiles"]
        table_widget.setColumnCount(len(column_titles))
        table_widget.setHorizontalHeaderLabels(column_titles)
        column_widths = [350, 90, 100]
        for i, width in enumerate(column_widths):
            table_widget.setColumnWidth(i, width)
        table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        for row_index, session in sessions.iterrows():
            table_widget.insertRow(row_index)
            table_widget.setItem(row_index, 0, QTableWidgetItem(session["name"]))
            table_widget.setItem(row_index, 1, QTableWidgetItem(session["save_date"]))
            table_widget.setItem(
                row_index, 2, QTableWidgetItem(str(session["number_of_tiles"]))
            )

            # flag read-only after filling
            for col_index in range(table_widget.columnCount()):
                if item := table_widget.item(row_index, col_index):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        layout.addWidget(table_widget)

        if origin == "load":
            radio_load_as_played = QRadioButton("Load as played", self)
            radio_load_as_played.setChecked(True)
            radio_simulate_placement = QRadioButton(
                "Load simulated tile placement", self
            )
            radio_simulate_tile_by_tile = QRadioButton(
                "Load/simulate tile by tile", self
            )

            layout.addWidget(radio_load_as_played)
            layout.addWidget(radio_simulate_placement)
            layout.addWidget(radio_simulate_tile_by_tile)

            layout.addWidget(QLabel(
                "Please note: The application may seem unresponsive while loading larger session"
            ))

            # Add a button to confirm loading the selected session
            load_button = QPushButton("Load Session")
            load_button.clicked.connect(
                lambda: self.confirm_load(
                    sessions,
                    table_widget.selectedItems(),
                    radio_simulate_placement.isChecked(),
                    radio_simulate_tile_by_tile.isChecked(),
                    dialog,
                )
            )
            layout.addWidget(load_button)
        elif origin == "delete":
            # Add a button to confirm loading the selected session
            load_button = QPushButton("Delete Session")
            load_button.clicked.connect(
                lambda: self.confirm_delete(
                    sessions, table_widget.selectedItems(), dialog
                )
            )
            layout.addWidget(load_button)

        dialog.setLayout(layout)
        dialog.exec()

    def confirm_delete(self, sessions, selection, dialog):
        selected = list({item.row() for item in selection})
        if len(selected) != 1:
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm delete")
        msg_box.setText(
            f"Are you sure you want to delete the session {sessions.iloc[selected[0]]['name']}?"
        )
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        result = msg_box.exec()
        if result == QMessageBox.Yes:
            self.trigger_delete_session.emit(sessions.iloc[selected[0]]["id"])

        dialog.accept()

    def confirm_load(self, sessions, selection,
                     load_simulated, load_tile_by_tile, dialog):
        selected_rows = list({item.row() for item in selection})
        if len(selected_rows) != 1:
            return

        self.trigger_reset_session.emit()
        self.trigger_load_session.emit(
            (sessions.iloc[selected_rows[0]]["id"], load_simulated, load_tile_by_tile)
        )
        dialog.accept()

    @Slot(tuple)
    def fill_tile_by_tile(self, data):
        auto_compute = True
        auto_place = False
        if isinstance(data, pd.DataFrame):
            # initial setup for tile by tile placement from a session load
            self.trigger_reset_session.emit()

            self.tile_by_tile_data = data
            self.tile_by_tile_index = 0
            auto_place = True  # ensure to directly place first tile

        elif self.tile_by_tile_data is not None and self.tile_by_tile_index >= 0:
            self.tile_by_tile_index += 1
        else:
            # we did not trigger tile by tile placement
            return

        if (
            not self.tile_by_tile_data.empty
            and self.tile_by_tile_index < self.tile_by_tile_data.shape[0]
        ):
            row = self.tile_by_tile_data.iloc[self.tile_by_tile_index]

            self.trigger_next_tile.emit(
                (row["side_type_seq"], row["center_type"], auto_compute, auto_place)
            )
        else:
            self.tile_by_tile_data = None
            self.tile_by_tile_index = -1

    @Slot()
    def reset_tile_by_tile(self):
        self.tile_by_tile_data = None
        self.tile_by_tile_index = -1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWidget()
    window.show()
    sys.exit(app.exec())
