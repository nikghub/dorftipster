import pytest

from src.side_type import SideType

def test_lt():
    expected_order = [
        SideType.UNKNOWN,
        SideType.CROPS,
        SideType.GREEN,
        SideType.HOUSE,
        SideType.PONDS,
        SideType.RIVER,
        SideType.STATION,
        SideType.TRAIN,
        SideType.WOODS
    ]

    assert all([a == b for a, b in zip(expected_order, sorted(SideType.all_types()))])

def test_is_valid():
    for type in SideType.all_types():
        assert SideType.is_valid(type)
        assert SideType.is_valid(type.value)

    assert not SideType.is_valid(None)
    assert not SideType.is_valid("ü")
    assert not SideType.is_valid("some gargabe")

def test_from_character():
    assert SideType.from_character(None) == SideType.UNKNOWN

    for type in SideType.all_types():
        assert SideType.from_character(type.value) == type
        assert SideType.from_character(type.value.lower()) == type
        assert SideType.from_character(type.value.upper()) == type

    with pytest.raises(ValueError):
        SideType.from_character("ü")

def test_to_string():
    assert SideType.to_string()