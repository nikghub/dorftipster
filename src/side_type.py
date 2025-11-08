from enum import IntEnum
from functools import lru_cache

class SideType(IntEnum):
    # types that may be placed against any
    WOODS = 0
    HOUSE = 1
    GREEN = 2
    CROPS = 3
    PONDS = 4  # may be water or land
    STATION = 5  # connects with any type including water and train
    # types that may only be placed against similar type
    RIVER = 6
    TRAIN = 7

    UNKNOWN = 8

    @classmethod
    @lru_cache(maxsize=None)
    def all_types(cls):
        return tuple(cls)

    @classmethod
    @lru_cache(maxsize=None)
    def get_values(cls):
        return tuple(t for t in cls if t != cls.UNKNOWN)

    @classmethod
    @lru_cache(maxsize=None)
    def is_equivalent_to_green(cls, side_type):
        return side_type in (cls.STATION, cls.GREEN, cls.PONDS)

    @classmethod
    @lru_cache(maxsize=20)
    def is_valid(cls, input_value):
        if input_value is None or input_value == "":
            return False
        if isinstance(input_value, cls):
            return True
        if not isinstance(input_value, str):
            return False
        try:
            cls.from_character(input_value)
        except ValueError:
            return False
        return True

    @classmethod
    @lru_cache(maxsize=None)
    def extract_type(cls, input_value):
        if isinstance(input_value, cls):
            return input_value
        if isinstance(input_value, int):
            return cls(input_value)
        return cls.from_character(input_value)

    @classmethod
    @lru_cache(maxsize=20)
    def from_character(cls, char):
        if not char:
            return cls.UNKNOWN
        try:
            return SIDE_TYPE_CHAR_MAP[char.upper()]
        except KeyError:
            raise ValueError(f"No enum member with character '{char}'")

    @lru_cache(maxsize=None)
    def to_character(self):
        return SIDE_TYPE_TO_CHAR[self]

    @classmethod
    @lru_cache(maxsize=None)
    def to_string(cls):
        string = ""
        for member in cls:
            if member == cls.WOODS:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Woods/Trees\n"
            elif member == cls.HOUSE:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Houses\n"
            elif member == cls.GREEN:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Green/Plains\n"
            elif member == cls.CROPS:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Crops/Fields\n"
            elif member == cls.PONDS:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Ponds/Water\n"
            elif member == cls.STATION:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Station (Watertemple)\n"
            elif member == cls.RIVER:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Rivers\n"
            elif member == cls.TRAIN:
                string += f"{SIDE_TYPE_TO_CHAR[member]} - Train tracks\n"

        return string

SIDE_TYPE_CHAR_MAP = {
    'W': SideType.WOODS,
    'H': SideType.HOUSE,
    'G': SideType.GREEN,
    'C': SideType.CROPS,
    'P': SideType.PONDS,
    'S': SideType.STATION,
    'R': SideType.RIVER,
    'T': SideType.TRAIN,
    '?': SideType.UNKNOWN,
}

SIDE_TYPE_TO_CHAR = {v: k for k, v in SIDE_TYPE_CHAR_MAP.items()}