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
    def get_all_values(cls):
        return tuple(cls)

    @classmethod
    @lru_cache(maxsize=None)
    def get_side_values(cls):
        return tuple(v for v in cls if v != cls.CENTER)

    @classmethod
    @lru_cache(maxsize=None)
    def get_index(cls, subsection):
        return subsection.value

    @classmethod
    @lru_cache(maxsize=None)
    def at_index(cls, index):
        return cls(index % len(cls.get_side_values()))