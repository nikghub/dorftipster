import pytest

from src.tile_subsection import TileSubsection

def test_get_all_values_returns_all_members_in_order():
    all_vals = TileSubsection.get_all_values()
    assert isinstance(all_vals, tuple)
    assert all_vals == tuple(TileSubsection)
    assert all_vals[-1] == TileSubsection.CENTER


def test_get_side_values_excludes_center():
    side_vals = TileSubsection.get_side_values()
    all_vals = TileSubsection.get_all_values()
    assert len(side_vals) == len(all_vals) - 1
    assert TileSubsection.CENTER not in side_vals
    assert side_vals[-1] == TileSubsection.UPPER_LEFT


def test_get_index_returns_correct_positions():
    assert TileSubsection.get_index(TileSubsection.TOP) == 0
    assert TileSubsection.get_index(TileSubsection.UPPER_LEFT) == 5
    assert TileSubsection.get_index(TileSubsection.CENTER) == 6


@pytest.mark.parametrize("index,expected", [
    (0, TileSubsection.TOP),
    (5, TileSubsection.UPPER_LEFT),
    (6, TileSubsection.TOP),  # wrap around
    (7, TileSubsection.UPPER_RIGHT),  # wrap around again
])
def test_at_index_wraps_correctly(index, expected):
    result = TileSubsection.at_index(index)
    assert result == expected


def test_lt_comparison_uses_value_string_ordering():
    assert (TileSubsection.TOP < TileSubsection.UPPER_RIGHT) == ('TOP' < 'UR')
    assert not (TileSubsection.BOTTOM < TileSubsection.BOTTOM)

def test_class_methods_work_after_cache_initialization():
    # Ensure that the class methods work correctly after cache initialization
    all_values = TileSubsection.get_all_values()
    side_values = TileSubsection.get_side_values()
    index_of_lower_right = TileSubsection.get_index(TileSubsection.LOWER_RIGHT)
    at_index_2 = TileSubsection.at_index(2)

    assert all_values == tuple(TileSubsection)
    assert side_values == tuple(TileSubsection)[:-1]
    assert index_of_lower_right == 2
    assert at_index_2 == TileSubsection.LOWER_RIGHT