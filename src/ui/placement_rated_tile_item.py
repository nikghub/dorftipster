from PySide6.QtCore import QPointF

from src.ui.constants import UIConstants
from src.tile import Tile

from src.ui.tile_item import TileItem


class PlacementRatedTileItem(TileItem):
    def __init__(self, tile, neighbor_candidate):
        super().__init__(tile, elevate=True)

        self.neighbor_candidate = neighbor_candidate

    def paint(self, painter, option, widget):
        border_margin_factor, radius = self.get_border_margin_and_radius()

        # draw outer border considering the placement, if the candidate were to be placed
        perspective_placement = None
        if self.neighbor_candidate is not None:
            perspective_placement = self.tile.get_placement_considering_neighbor_tile(
                self.neighbor_candidate.tile
            )
            perspective_placement_color = UIConstants.PLACEMENT_COLORS[
                perspective_placement
            ]
            radius -= self.draw_hexagon(
                painter,
                self.center,
                radius,
                color=perspective_placement_color,
                border_color=UIConstants.RATED_BORDER_COLOR,
                border_width=UIConstants.RATED_BORDER_WIDTH,
            )
            radius -= UIConstants.RATED_PERSPECTIVE_BORDER_WIDTH

        # draw inner hexagon considering the current placement
        self.draw_hexagon(
            painter,
            self.center,
            radius,
            color=UIConstants.PLACEMENT_COLORS[self.tile.get_placement()],
            border_color=UIConstants.RATED_BORDER_COLOR,
            border_width=UIConstants.RATED_BORDER_WIDTH,
        )

        # highlight option to perfectly close a tile
        if perspective_placement == Tile.Placement.PERFECTLY_CLOSED:
            # adjust center to consider the border margin
            center = QPointF(
                self.center.x() - border_margin_factor / 2,
                self.center.y() - border_margin_factor / 2,
            )
            self.draw_tile_centered_text(
                painter,
                center,
                text=UIConstants.PERFECTLY_CLOSED_TILE_TEXT,
                text_color=UIConstants.TEXT_PLACEMENT_COLORS[
                    Tile.Placement.PERFECTLY_CLOSED
                ],
                background_color=UIConstants.PLACEMENT_COLORS[
                    Tile.Placement.PERFECTLY_CLOSED
                ],
            )
