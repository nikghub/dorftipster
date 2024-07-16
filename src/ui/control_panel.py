from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QGroupBox,
)
from PySide6.QtCore import Slot, Signal

from src.constants import UIConstants


class FocusLineEdit(QLineEdit):
    focus_received = Signal()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focus_received.emit()


class ControlPanel(QWidget):
    compute_button_clicked = Signal(tuple)
    compute_button_repeated = Signal()
    trigger_message_display = Signal(tuple)
    trigger_display_help = Signal()
    trigger_display_stats = Signal()
    toggle_map_display = Signal()

    def __init__(self, session):
        super().__init__()
        self.setFixedSize(
            UIConstants.CONTROL_PANEL_WIDTH, UIConstants.LOWER_LAYOUT_HEIGHT
        )
        self.setup_ui()
        self.place_button.setEnabled(False)
        self.undo_button.setEnabled(False)
        self.session = session

        self.submitted_tile_sequence = None
        self.submitted_tile_center = None
        self.reset()

    def setup_ui(self):
        layout = QVBoxLayout()

        group_box = QGroupBox(UIConstants.NEXT_TILE_TITLE)
        group_box_layout = QVBoxLayout()

        next_tile_sequence_layout = QHBoxLayout()
        next_tile_sequence_layout.addWidget(
            QLabel(UIConstants.NEXT_TILE_SIDE_SEQ_TITLE + ":")
        )
        self.next_tile_sequence = FocusLineEdit()
        self.next_tile_sequence.setFixedWidth(85)
        next_tile_sequence_layout.addWidget(self.next_tile_sequence)
        group_box_layout.addLayout(next_tile_sequence_layout)

        next_tile_center_layout = QHBoxLayout()
        next_tile_center_layout.addWidget(
            QLabel(UIConstants.NEXT_TILE_CENTER_TITLE + ":")
        )
        self.next_tile_center = FocusLineEdit()
        self.next_tile_center.setFixedWidth(30)
        next_tile_center_layout.addWidget(self.next_tile_center)
        group_box_layout.addLayout(next_tile_center_layout)

        group_box.setLayout(group_box_layout)
        layout.addWidget(group_box)

        self.compute_button = QPushButton("Compute")
        layout.addWidget(self.compute_button)

        place_undo_layout = QHBoxLayout()
        self.place_button = QPushButton("Place tile")
        place_undo_layout.addWidget(self.place_button)
        self.undo_button = QPushButton("Undo last tile")
        place_undo_layout.addWidget(self.undo_button)
        layout.addLayout(place_undo_layout)

        info_layout = QHBoxLayout()
        self.show_stats_button = QPushButton("Game stats")
        info_layout.addWidget(self.show_stats_button)
        self.show_help_button = QPushButton("Show help")
        info_layout.addWidget(self.show_help_button)
        layout.addLayout(info_layout)
        self.toggle_session_display_button = QPushButton("Toggle session map")
        layout.addWidget(self.toggle_session_display_button)

        self.next_tile_seen = QLabel()
        layout.addWidget(self.next_tile_seen)

        self.setLayout(layout)

        self.next_tile_sequence.returnPressed.connect(self.handle_compute)
        self.next_tile_center.returnPressed.connect(self.handle_compute)
        self.compute_button.clicked.connect(self.handle_compute)
        self.show_stats_button.clicked.connect(self.handle_show_stats)
        self.show_help_button.clicked.connect(self.handle_show_help)
        self.toggle_session_display_button.clicked.connect(
            self.handle_toggle_session_map
        )

    @Slot()
    def handle_compute(self):
        next_tile_sequence = self.next_tile_sequence.text()
        next_tile_center = self.next_tile_center.text()

        if (
            next_tile_sequence == self.submitted_tile_sequence
            and next_tile_center == self.submitted_tile_center
        ):
            self.compute_button_repeated.emit()  # compute clicked but no change in input
            return

        # either "enter" pressed in input textfield or "compute" button was clicked
        self.submitted_tile_sequence = next_tile_sequence
        self.submitted_tile_center = next_tile_center
        self.compute_button_clicked.emit((next_tile_sequence, next_tile_center, None))

    @Slot()
    def handle_show_stats(self):
        self.trigger_display_stats.emit()

    @Slot()
    def handle_show_help(self):
        self.trigger_display_help.emit()

    @Slot()
    def handle_toggle_session_map(self):
        self.toggle_map_display.emit()

    @Slot()
    def reset(self):
        self.next_tile_sequence.clear()
        self.update_similar_tiles_seen()
        self.next_tile_center.clear()
        self.place_button.setEnabled(False)
        self.undo_button.setEnabled(False)

        self.submitted_tile_sequence = None
        self.submitted_tile_center = None

    @Slot(bool)
    def set_undo_button_enabled(self, enabled):
        self.undo_button.setEnabled(enabled)

    @Slot(bool)
    def set_place_button_enabled(self, enabled):
        self.place_button.setEnabled(enabled)

    @Slot(tuple)
    def focus_next_sequence(self, event):
        self.next_tile_sequence.setFocus()

    @Slot(tuple)
    def focus_place_button(self, event):
        self.place_button.setFocus()

    @Slot(int)
    def update_similar_tiles_seen(self, seen=-1):
        part = str(seen) if seen >= 0 else "?"
        self.next_tile_seen.setText(UIConstants.NEXT_TILE_SEEN_TITLE.format(x=part))

    @Slot(tuple)
    def prefill_next_tile(self, args):
        side_type_seq, center_type, auto_compute, auto_place = args
        self.next_tile_sequence.setText(side_type_seq)
        self.next_tile_center.setText(center_type)
        if auto_compute:
            self.compute_button.clicked.emit()
            if auto_place:
                self.place_button.clicked.emit()
            else:
                self.place_button.setFocus()
        else:
            self.place_button.setEnabled(False)
            self.compute_button.setFocus()

        self.undo_button.setEnabled(False)
