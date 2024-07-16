from src.constants import UIConstants

from src.ui.tile_item import TileItem


class OpenCoordinateItem(TileItem):
    def __init__(self, coordinates, highlight=False, elevate=False):
        super().__init__(coordinates=coordinates, highlight=highlight, elevate=elevate)
        self.coordinates = coordinates

    def paint(self, painter, option, widget):
        radius = UIConstants.BASE_RADIUS * (
            1 - UIConstants.OPEN_COORDINATES_BORDER_MARGIN_FACTOR
        )
        color = UIConstants.WATCH_COLORS[UIConstants.WatchStatus.UNWATCHED]
        if self.elevate:
            color = UIConstants.WATCH_COLORS[UIConstants.WatchStatus.WATCHED]
        elif self.highlight:
            color = UIConstants.WATCH_COLORS[UIConstants.WatchStatus.SELECTED]
        self.draw_hexagon(
            painter,
            self.center,
            radius,
            color=color,
            border_color=UIConstants.OPEN_COORDINATES_BORDER_COLOR,
        )
