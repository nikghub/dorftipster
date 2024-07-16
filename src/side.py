from enum import Enum

from src.side_type import SideType

class Side:
    class Placement(Enum):
        UNKNOWN_MATCH = -2
        NOT_POSSIBLE = -1
        IMPERFECT_MATCH = 0
        PERFECT_MATCH = 1

    def __init__(self, side_type=SideType.UNKNOWN, isolated=False):
        self.type = side_type
        self.placement = self.Placement.UNKNOWN_MATCH
        self.isolated = isolated

    def __eq__(self, other):
        if isinstance(other, Side):
            return self.type == other.type and\
                   self.placement == other.placement and\
                   self.isolated == other.isolated
        return False
