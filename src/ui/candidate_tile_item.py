from PySide6.QtCore import QPointF

from src.constants import UIConstants

from src.ui.tile_item import TileItem


class CandidateTileItem(TileItem):
    def __init__(self, candidate, tile_color, highlight=False):
        super().__init__(candidate.tile, highlight)
        self.candidate = candidate
        self.tile_color = tile_color

    def paint(self, painter, option, widget):
        # elevate for border and radius
        self.elevate = True
        border_margin_factor, radius = self.get_border_margin_and_radius()
        self.elevate = False

        tile_placement = self.candidate.tile.get_placement()
        self.draw_emphasised_hexagon(
            painter,
            radius,
            color=self.tile_color,
            border_color=UIConstants.PLACEMENT_COLORS[tile_placement],
        )

        # adjust center to consider the border margin
        center = QPointF(
            self.center.x() - border_margin_factor / 2,
            self.center.y() - border_margin_factor / 2,
        )

        self.draw_tile_centered_text(
            painter,
            center,
            text=str(int(self.candidate.rating)),
            text_color=UIConstants.TEXT_PLACEMENT_COLORS[tile_placement],
            background_color=UIConstants.PLACEMENT_COLORS[tile_placement],
        )
