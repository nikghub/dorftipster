import pytest

from src.side_type import SideType, SIDE_TYPE_TO_CHAR

def test_is_valid():
    for type in SideType.all_types():
        assert SideType.is_valid(type)
        assert SideType.is_valid(SIDE_TYPE_TO_CHAR[type])

    assert not SideType.is_valid(None)
    assert not SideType.is_valid("ü")
    assert not SideType.is_valid("some gargabe")

    assert not SideType.is_valid(3.14)

def test_from_character():
    assert SideType.from_character(None) == SideType.UNKNOWN

    for type in SideType.all_types():
        assert SideType.from_character(SIDE_TYPE_TO_CHAR[type]) == type
        assert SideType.from_character(SIDE_TYPE_TO_CHAR[type].lower()) == type
        assert SideType.from_character(SIDE_TYPE_TO_CHAR[type].upper()) == type

    with pytest.raises(ValueError):
        SideType.from_character("ü")

def test_to_string():
    assert SideType.to_string()

def test_extract_type():
    for type in SideType.all_types():
        SideType.extract_type.cache_clear()
        assert SideType.extract_type(type) == type
        SideType.extract_type.cache_clear()
        assert SideType.extract_type(SIDE_TYPE_TO_CHAR[type]) == type
        SideType.extract_type.cache_clear()
        assert SideType.extract_type(type.value) == type