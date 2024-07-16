from enum import Enum

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
    def get_all_values(cls):
        return list(cls.__members__.values())

    @classmethod
    def get_side_values(cls):
        return cls.get_all_values()[:-1]

    @classmethod
    def get_index(cls, subsection):
        return list(cls.__members__).index(subsection.name)

    @classmethod
    def at_index(cls, index):
        return cls.get_side_values()[index % len(cls.get_side_values())]
