from src.side import Side
from src.side_type import SideType

def test_eq():
    side_0 = Side(SideType.GREEN)
    side_1 = Side(SideType.GREEN)
    side_2 = Side(SideType.CROPS)

    assert side_0 == side_1
    assert side_0 != side_2

    side_0.placement = Side.Placement.IMPERFECT_MATCH
    assert side_0 != side_1
    side_1.placement = Side.Placement.IMPERFECT_MATCH
    assert side_0 == side_1
    side_1.placement = Side.Placement.NOT_POSSIBLE
    assert side_0 != side_1

    side_2.placement = Side.Placement.PERFECT_MATCH
    assert side_2 != side_0
    assert side_2 != side_1

    # different types
    assert side_0 != 10
    assert side_0 != "a string"