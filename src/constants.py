from src.side_type import SideType

class Constants:
    # compatibility of a type with group types
    COMPATIBLE_GROUP_TYPES = {
        SideType.CROPS : [SideType.CROPS],
        SideType.HOUSE : [SideType.HOUSE],
        SideType.RIVER : [SideType.RIVER, SideType.PONDS, SideType.STATION],
        SideType.PONDS : [SideType.PONDS, SideType.RIVER, SideType.STATION],
        SideType.TRAIN : [SideType.TRAIN, SideType.STATION],
        SideType.STATION : [SideType.STATION, SideType.RIVER, SideType.TRAIN, SideType.PONDS],
        SideType.WOODS : [SideType.WOODS]
        }
    # types that allow a group creation
    ALLOWED_GROUP_TYPES = [
        SideType.CROPS,
        SideType.HOUSE,
        SideType.RIVER,
        SideType.PONDS,
        SideType.TRAIN,
        SideType.WOODS
    ]


class DatabaseConstants:
    DB_NAME = "sessions.db"

    AUTOSAVE_NAME = "__autosave__"
