from math import pi, cos, sin

from PySide6.QtWidgets import QGraphicsPolygonItem
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import Qt, QBrush, QPen, QPolygonF, QFont, QFontMetrics

from src.tile_subsection import TileSubsection
from src.side_type import SideType
from src.ui.constants import UIConstants

from src.ui.utils import to_scene_coordinates


class TileItem(QGraphicsPolygonItem):
    def __init__(self, tile=None, highlight=False, elevate=False, coordinates=None):
        super().__init__()
        self.tile = tile
        self.highlight = highlight
        self.elevate = elevate

        if coordinates:
            self.center = to_scene_coordinates(coordinates)
        else:
            self.center = to_scene_coordinates(tile.coordinates)

        points = []
        for i in range(6):
            angle_rad = i * (pi / 3)
            points.append(
                QPointF(
                    self.center.x() + UIConstants.BASE_RADIUS * cos(angle_rad),
                    self.center.y() + UIConstants.BASE_RADIUS * sin(angle_rad),
                )
            )
        hexagon = QPolygonF(points)
        self.setPolygon(hexagon)

    def contains_point(self, point):
        return self.polygon().containsPoint(point, Qt.WindingFill)

    def draw_emphasised_hexagon(self, painter, radius, color, border_color):
        orig_radius = radius
        if self.highlight:
            # border on the very outside to highlight the currently selected candidate
            radius -= self.draw_hexagon(
                painter,
                self.center,
                radius,
                color=UIConstants.HIGHLIGHT_INNER_BORDER_COLOR,
                border_color=UIConstants.HIGHLIGHT_OUTER_BORDER_COLOR,
                border_width=UIConstants.HIGHLIGHT_BORDER_WIDTH,
            )
            radius -= UIConstants.HIGHLIGHT_BORDER_WIDTH

            # placement color indication per side of the candidate tile
            for subsection in TileSubsection.get_side_values():
                self.draw_triangle(
                    painter,
                    self.tile,
                    self.center,
                    radius,
                    subsection,
                    landscape_color=False,
                )
            radius -= UIConstants.RATED_PERSPECTIVE_BORDER_WIDTH

        border_width = UIConstants.BORDER_WIDTH
        if self.elevate:
            border_color = UIConstants.ELEVATE_BORDER_COLOR
            border_width = UIConstants.ELEVATE_BORDER_WIDTH
        elif self.highlight:
            border_color = UIConstants.HIGHLIGHT_INNER_BORDER_COLOR
            border_width = UIConstants.HIGHLIGHT_INNER_BORDER_WIDTH

        # hexaon with the actual color with a (inner) border around it
        radius -= self.draw_hexagon(
            painter, self.center, radius, color, border_color, border_width
        )

        # return the thickness of the highlighting wrapper
        return orig_radius - radius

    def get_border_margin_and_radius(self):
        if self.highlight:
            border_margin_factor = UIConstants.HIGHLIGHT_BORDER_MARGIN_FACTOR
        elif self.elevate:
            border_margin_factor = UIConstants.ELEVATE_BORDER_MARGIN_FACTOR
        else:
            border_margin_factor = UIConstants.BORDER_MARGIN_FACTOR

        return (
            border_margin_factor,
            UIConstants.BASE_RADIUS * (1 - border_margin_factor),
        )

    def draw_triangle(self, painter, tile, center, radius, subsection,
                      landscape_color=True):
        # Ensure correct tilt of the triangle as per subsection of the hexagon
        tilt = {s: (i - 2) % 6 for i, s in enumerate(TileSubsection.get_side_values())}

        start_angle_rad = (tilt[subsection] % 6) * (pi / 3)
        end_angle_rad = ((tilt[subsection] + 1) % 6) * (pi / 3)

        def get_points(r):
            return [
                center,
                QPointF(
                    center.x() + r * cos(start_angle_rad),
                    center.y() + r * sin(start_angle_rad),
                ),
                QPointF(
                    center.x() + r * cos(end_angle_rad),
                    center.y() + r * sin(end_angle_rad),
                ),
            ]

        points = get_points(radius)
        painter.setPen(Qt.NoPen)
        if landscape_color:
            painter.setBrush(
                QBrush(UIConstants.LANDSCAPE_COLORS[tile.get_side(subsection).type])
            )
        else:
            painter.setBrush(
                QBrush(
                    UIConstants.PLACEMENT_COLORS[tile.get_side(subsection).placement]
                )
            )
        painter.drawPolygon(QPolygonF(points))

        if landscape_color and tile.get_side(subsection).isolated:
            # draw another triangle with green which will
            # disconnect the actual type color from the center
            points = get_points(
                radius * UIConstants.ISOLATED_SIDE_TYPE_RADIUS_REDUCTION_FACTOR
            )
            painter.setBrush(QBrush(UIConstants.LANDSCAPE_COLORS[SideType.GREEN]))
            painter.drawPolygon(QPolygonF(points))

    def draw_hexagon(
        self,
        painter,
        center,
        radius,
        color,
        border_color=None,
        border_width=UIConstants.BORDER_WIDTH,
    ):
        points = []

        if border_color is not None:
            radius -= border_width / 2

        for i in range(6):
            angle_rad = i * (pi / 3)
            points.append(
                QPointF(
                    center.x() + radius * cos(angle_rad),
                    center.y() + radius * sin(angle_rad),
                )
            )
        painter.setBrush(QBrush(color))
        original_pen = painter.pen()
        if border_color is not None:
            pen = QPen(border_color)
            pen.setWidth(border_width)
            painter.setPen(pen)
        painter.drawPolygon(QPolygonF(points))
        painter.setPen(original_pen)

        # return width of border
        if border_color is not None:
            return border_width
        return 0

    def draw_tile_centered_text(
        self, painter, center, text, text_color, background_color
    ):
        original_pen = painter.pen()
        original_font = painter.font()

        font = QFont("Arial", UIConstants.MAP_TEXT_FONT_SIZE)
        font.setWeight(QFont.Bold)
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(text)
        text_rect.moveCenter(QPoint(center.x(), center.y()))

        painter.setBrush(QBrush(background_color))
        painter.setPen(Qt.NoPen)
        rect = text_rect.adjusted(-4, -2, 4, 2)  # Adjust the rectangle for padding
        painter.drawRoundedRect(rect, 10, 10)

        # Draw the text over the background box
        painter.setPen(QPen(text_color))
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignCenter, text)

        # Restore the original pen and font
        painter.setPen(original_pen)
        painter.setFont(original_font)
