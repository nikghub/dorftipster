from enum import IntEnum
from functools import lru_cache

class TileSubsection(IntEnum):
    TOP = 0
    UPPER_RIGHT = 1
    LOWER_RIGHT = 2
    BOTTOM = 3
    LOWER_LEFT = 4
    UPPER_LEFT = 5
    CENTER = 6

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