from enum import Enum
from functools import lru_cache

class TileSubsection(Enum):
    TOP = 'TOP'
    UPPER_RIGHT = 'UR'
    LOWER_RIGHT = 'LR'
    BOTTOM = 'BOT'
    LOWER_LEFT = 'LL'
    UPPER_LEFT = 'UL'

    CENTER = 'CENTER'

    def __lt__(self, other):
        return self.value < other.value

    @classmethod
    @lru_cache(maxsize=None)
    def _all_values(cls):
        return tuple(cls.__members__.values())

    @classmethod
    @lru_cache(maxsize=None)
    def _side_values(cls):
        return tuple(cls._all_values()[:-1])

    @classmethod
    @lru_cache(maxsize=None)
    def _name_to_index(cls):
        return {name: i for i, name in enumerate(cls.__members__)}

    @classmethod
    def get_all_values(cls):
        return cls._all_values()

    @classmethod
    def get_side_values(cls):
        return cls._side_values()

    @classmethod
    def get_index(cls, subsection):
        return cls._name_to_index()[subsection.name]

    @classmethod
    def at_index(cls, index):
        side_vals = cls._side_values()
        return side_vals[index % len(side_vals)]