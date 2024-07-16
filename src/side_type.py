from enum import Enum

class SideType(Enum):
    # types that may be placed against any
    WOODS = 'W'
    HOUSE = 'H'
    GREEN = 'G'
    CROPS = 'C'
    PONDS = 'P' # may be water or land
    STATION = 'S' # connects with any type including water and train
    # types that may only be placed against similar type
    RIVER = 'R'
    TRAIN = 'T'

    UNKNOWN = '?'

    def __lt__(self, other):
        return self.value < other.value

    @classmethod
    def all_types(cls):
        return list(cls)

    @classmethod
    def get_values(cls):
        return list(cls.__members__.values())[:-1]

    @classmethod
    def is_equivalent_to_green(cls, side_type):
        return side_type in [SideType.STATION, SideType.GREEN, SideType.PONDS]

    @classmethod
    def is_valid(cls, input_string):
        if input_string is None:
            return False
        if isinstance(input_string, SideType):
            return True

        try:
            cls.from_character(input_string)
        except ValueError:
            return False
        return True

    @classmethod
    def extract_type(cls, input_string):
        if isinstance(input_string, SideType):
            return input_string

        return cls.from_character(input_string)

    @classmethod
    def from_character(cls, char):
        if char is None:
            return SideType.UNKNOWN

        for member in cls:
            if member.value == char.upper():
                return member
        raise ValueError(f"No enum member with character '{char}'")

    def to_character(self):
        return self.value

    @classmethod
    def to_string(cls):
        string = ""
        for member in cls:
            if member == SideType.WOODS:
                string += f"{member.value} - Woods/Trees\n"
            elif member == SideType.HOUSE:
                string += f"{member.value} - Houses\n"
            elif member == SideType.GREEN:
                string += f"{member.value} - Green/Plains\n"
            elif member == SideType.CROPS:
                string += f"{member.value} - Crops/Fields\n"
            elif member == SideType.PONDS:
                string += f"{member.value} - Ponds/Water\n"
            elif member == SideType.STATION:
                string += f"{member.value} - Station (Watertemple)\n"
            elif member == SideType.RIVER:
                string += f"{member.value} - Rivers\n"
            elif member == SideType.TRAIN:
                string += f"{member.value} - Train tracks\n"

        return string
