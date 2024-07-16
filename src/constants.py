from enum import Enum

from PySide6.QtGui import QColor

from src.tile import Tile
from src.side import Side
from src.side_type import SideType


class UIConstants:
    class Layer(Enum):
        LANDSCAPES = 0
        PLACEMENT_RATINGS = 1

        @classmethod
        def get_index(cls, val):
            return list(cls.__members__).index(val.name)

        @classmethod
        def at_index(cls, index):
            values = list(cls.__members__.values())
            return values[index % len(values)]

    class WatchStatus(Enum):
        UNWATCHED = "UNWATCHED"
        WATCHED = "WATCHED"
        SELECTED = "SELECTED"

    TITLE = "Dorftipster - Dorfromantik tile placement helper"
    NEXT_TILE_TITLE = "Next tile definition"
    NEXT_TILE_SIDE_SEQ_TITLE = "Side types"
    NEXT_TILE_CENTER_TITLE = "Center type"
    NEXT_TILE_SEEN_TITLE = "Tiles with similar sides so far: {x}"

    NO_INDEX = "---"
    NO_RATING = "---"
    IS_WATCH_CANDIDATE_INDICATOR = "*"

    LOWER_LAYOUT_HEIGHT = 270

    CONTROL_PANEL_WIDTH = 250
    CANDIDATE_LIST_WIDTH = 300
    CANDIDATE_NEIGHBOR_MAP_MIN_WIDTH = 300
    WATCHED_CANDIDATE_WIDTH = 250
    LEGEND_WIDTH = 300
    LEGEND_TEXT_COLOR = QColor("black")

    BACKGROUND_COLOR = QColor("gainsboro")

    LANDSCAPE_COLORS = {
        SideType.WOODS: QColor("forestgreen"),
        SideType.HOUSE: QColor("firebrick"),
        SideType.GREEN: QColor("lightGreen"),
        SideType.CROPS: QColor("gold"),
        SideType.PONDS: QColor("aqua"),
        SideType.STATION: QColor("plum"),
        SideType.RIVER: QColor("mediumblue"),
        SideType.TRAIN: QColor("chocolate"),
    }

    TEXT_PLACEMENT_COLORS = {
        Tile.Placement.PERFECTLY_CLOSED: QColor("black"),
        Tile.Placement.PERFECT: QColor("white"),
        Tile.Placement.IMPERFECT: QColor("white"),
    }

    PLACEMENT_COLORS = {
        Tile.Placement.PERFECTLY_CLOSED: QColor("gold"),
        Tile.Placement.PERFECT: QColor("teal"),
        Side.Placement.PERFECT_MATCH: QColor("teal"),
        Tile.Placement.IMPERFECT: QColor("orangered"),
        Side.Placement.IMPERFECT_MATCH: QColor("orangered"),
        Side.Placement.UNKNOWN_MATCH: QColor("lightgray"),
        Tile.Placement.UNKNOWN: QColor("lightgray"),
    }

    WATCH_COLORS = {
        WatchStatus.UNWATCHED: BACKGROUND_COLOR,
        WatchStatus.WATCHED: QColor("lightsteelblue"),
        WatchStatus.SELECTED: QColor("royalblue"),
    }

    class CandidatePlacementEvaluation(Enum):
        SUGGESTION = "SUGGESTION"
        BEST = "BEST"
        WORST = "WORST"

    CANDIDATE_PLACEMENT_EVALUATION_COLORS = {
        CandidatePlacementEvaluation.SUGGESTION: QColor("palegoldenrod"),
        CandidatePlacementEvaluation.BEST: QColor("white"),
        CandidatePlacementEvaluation.WORST: QColor("black"),
    }

    HIGHLIGHT_BORDER_MARGIN_FACTOR = -0.04
    HIGHLIGHT_OUTER_BORDER_COLOR = QColor("black")
    HIGHLIGHT_INNER_BORDER_COLOR = QColor("lightgray")
    HIGHLIGHT_BORDER_WIDTH = 2
    HIGHLIGHT_INNER_BORDER_WIDTH = 2

    ELEVATE_BORDER_MARGIN_FACTOR = 0.1
    ELEVATE_BORDER_COLOR = QColor("black")
    ELEVATE_BORDER_WIDTH = 2

    RATED_PERSPECTIVE_BORDER_WIDTH = 6
    RATED_BORDER_COLOR = QColor("black")
    RATED_BORDER_WIDTH = 1

    PERFECTLY_CLOSED_TILE_TEXT = "P"

    LANDSCAPE_BORDER_COLOR = QColor("dimgray")
    LANDSCAPE_CENTER_BORDER_COLOR = QColor("black")

    OPEN_COORDINATES_BORDER_MARGIN_FACTOR = 0.2
    OPEN_COORDINATES_BORDER_COLOR = LANDSCAPE_BORDER_COLOR

    BORDER_MARGIN_FACTOR = 0.03
    BORDER_WIDTH = 1

    BASE_RADIUS = 45
    MAP_TEXT_FONT_SIZE = 13.5

    ISOLATED_SIDE_TYPE_RADIUS_REDUCTION_FACTOR = 0.7


class DatabaseConstants:
    DB_NAME = "sessions.db"

    AUTOSAVE_NAME = "__autosave__"
