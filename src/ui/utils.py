from math import pi, cos, sin

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

from src.constants import UIConstants


def to_scene_coordinates(tile_coords):
    x_side_length = cos(pi / 3)
    y_side_length = sin(pi / 3) / 2

    x = UIConstants.BASE_RADIUS * x_side_length * tile_coords[0]
    y = UIConstants.BASE_RADIUS * y_side_length * tile_coords[1]

    # y-coordinate is inverted, as top-left point is (0,0)
    return QPointF(x, -y)


def get_candidate_rating_color(candidates, candidate):
    # highest rating candidates should be clearly highlighted
    if candidate.rating == candidates[0].rating:
        return UIConstants.CANDIDATE_PLACEMENT_EVALUATION_COLORS[
            UIConstants.CandidatePlacementEvaluation.SUGGESTION
        ]

    # otherwise compute normalized rating between 0 (worst) and 1 (best) for color coding
    min_r, max_r = [candidates[pos].rating for pos in [-1, 0]]
    normalized_r = (
        1.0 if (min_r == max_r) else (candidate.rating - min_r) / (max_r - min_r)
    )
    return QColor(*[255 * normalized_r for i in range(3)])
