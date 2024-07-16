from PySide6.QtCore import QPointF

from src.constants import UIConstants

from src.ui.tile_item import TileItem


class LandscapeTileItem(TileItem):
    def __init__(self, tile, candidate=None, highlight=False, elevate=False):
        super().__init__(tile, highlight, elevate)
        self.candidate = candidate

    def paint(self, painter, option, widget):
        border_margin_factor, radius = self.get_border_margin_and_radius()
        radius -= self.draw_emphasised_hexagon(
            painter,
            radius,
            # the color of the hexagon will only be relevant when highlighting
            color=UIConstants.HIGHLIGHT_OUTER_BORDER_COLOR,
            border_color=UIConstants.LANDSCAPE_BORDER_COLOR,
        )

        # as the border is a hexagon, we must ensure it stays visible as we draw triangles on top
        if self.highlight:
            radius -= UIConstants.BORDER_WIDTH

        # draw side types as triangles
        for subsection in self.tile.get_sides().keys():
            self.draw_triangle(
                painter,
                self.tile,
                self.center,
                radius,
                subsection,
                landscape_color=True,
            )

        # draw center type as inner hexagon, adjust center to consider the border margin
        center = QPointF(
            self.center.x() - border_margin_factor / 2,
            self.center.y() - border_margin_factor / 2,
        )
        self.draw_hexagon(
            painter,
            center,
            radius / 2,
            color=UIConstants.LANDSCAPE_COLORS[self.tile.get_center().type],
            border_color=UIConstants.LANDSCAPE_CENTER_BORDER_COLOR,
        )
