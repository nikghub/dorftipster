from enum import Enum

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QFont, QPen

from src.tile import Tile
from src.constants import UIConstants


class Legend(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(UIConstants.LEGEND_WIDTH, UIConstants.LOWER_LAYOUT_HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), UIConstants.BACKGROUND_COLOR)
        painter.setPen(QPen(UIConstants.LEGEND_TEXT_COLOR, 1.5))

        x = 10
        y = 0

        def draw_title(painter, text, font_size=10):
            nonlocal x, y
            y += 15
            painter.setFont(QFont("AnyStyle", font_size, QFont.Bold))
            painter.drawText(x, y, text)
            y += 5

        def draw_item(
            painter,
            color,
            text=None,
            underline_first_letter=False,
            radius=17,
            x_offset=0,
        ):
            nonlocal x, y
            painter.setBrush(color)
            painter.drawEllipse(x + x_offset, y, radius, radius)
            if text is not None:
                if isinstance(text, Enum):
                    text = text.name
                font = QFont("AnyStyle", 9)

                if underline_first_letter:
                    font.setUnderline(True)
                    painter.setFont(font)
                    painter.drawText(x + x_offset + radius + 5, y + radius - 5, text[0])

                font.setUnderline(False)
                painter.setFont(font)

                painter.drawText(x + x_offset + radius + 5, y + radius - 5, text)
            y += radius + 3

        draw_title(painter, "COLOR CODING", 9)

        draw_title(painter, "Placement rating")
        for label_enum, color in UIConstants.PLACEMENT_COLORS.items():
            if isinstance(label_enum, Tile.Placement):
                draw_item(painter, color, label_enum.name)

        draw_title(painter, "Candidate evaluation")
        cpe_items = UIConstants.CANDIDATE_PLACEMENT_EVALUATION_COLORS.items()
        for index, (label, color) in enumerate(cpe_items):
            draw_item(painter, color, label)
            if (index < len(cpe_items) - 1
                and label != UIConstants.CandidatePlacementEvaluation.SUGGESTION
            ):
                for dot in range(3):
                    draw_item(
                        painter, UIConstants.LEGEND_TEXT_COLOR, radius=2, x_offset=8
                    )

        # move to right side of legend
        x = 190
        y = 0

        draw_title(painter, "Landscapes")
        for label_enum, color in UIConstants.LANDSCAPE_COLORS.items():
            draw_item(painter, color, label_enum.name, underline_first_letter=True)

        draw_title(painter, "Watch status")
        for label_enum, color in UIConstants.WATCH_COLORS.items():
            draw_item(painter, color, label_enum.name)
