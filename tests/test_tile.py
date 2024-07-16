import pytest

from src.tile import Tile
from src.side import Side
from src.side_type import SideType
from src.tile_subsection import TileSubsection
from src.session import Session

from tests.utils import get_example_side_sequence, get_sequence, isolate_at_index

def test_extract_subsection_sides_side_sequence():
    for i in range(1, 7):
        input = get_example_side_sequence(i)
        if i in [1, 6]:
            expected_output = input
            if i == 1:
                expected_output = "".join([input[0] for i in range(6)])
            assert "".join(
                [SideType.to_character(side.type) for side in Tile.extract_subsection_sides(input).values()]
                ) == expected_output
        else:
            with pytest.raises(ValueError):
                Tile.extract_subsection_sides(input)

def test_extract_subsection_sides_side_types():
    for i in range(1, 7):
        input = get_example_side_sequence(i)
        input_side_type_list = [SideType.from_character(c) for c in input]
        if i in [1, 6]:
            expected_output = [Side(input_type, False) for input_type in input_side_type_list]
            if i == 1:
                expected_output = expected_output * 6
            assert expected_output ==  list(Tile.extract_subsection_sides(input_side_type_list).values())
        else:
            with pytest.raises(ValueError):
                Tile.extract_subsection_sides(input_side_type_list)

    for side_type in SideType.get_values():
        expected_output = [Side(side_type, False)] * 6
        assert list(Tile.extract_subsection_sides(side_type).values()) == expected_output
        assert list(Tile.extract_subsection_sides([side_type]).values()) == expected_output
        assert list(Tile.extract_subsection_sides([side_type]*6).values()) == expected_output

def test_extract_subsection_sides_isolation():
    example_sequence = \
        get_sequence([SideType.WOODS, SideType.HOUSE, SideType.WOODS, SideType.CROPS, SideType.WOODS, SideType.GREEN])
    for i in range(6):
        isolated_sequence = isolate_at_index(example_sequence, i)
        extracted_sides = Tile.extract_subsection_sides(isolated_sequence)
        assert len(extracted_sides) == len(example_sequence)
        for j, side in enumerate(extracted_sides.values()):
            assert SideType.to_character(side.type) == example_sequence[j]
            if i == j:
                assert side.isolated == True
            else:
                assert side.isolated == False

def test_extract_subsection_sides_isolation_single_char():
    single_char_type = SideType.CROPS
    single_char_sides = Tile.extract_subsection_sides(f"{single_char_type.value}")
    single_char_isolated_sides = Tile.extract_subsection_sides(f"({single_char_type.value})")
    assert list(single_char_sides.values()) == [Side(single_char_type, False)] * 6
    # isolation should be ignored for single type shortcut
    assert single_char_sides == single_char_isolated_sides

def test_extract_subsection_sides_isolation_singularity():
    # assert isolation may only ever be alone
    for i in range(6):
        sequence = get_sequence([SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.CROPS, SideType.WOODS], i)

        if i in [0,1,2,5]:
            with pytest.raises(ValueError):
                Tile.extract_subsection_sides(sequence)
        else:
            assert len(Tile.extract_subsection_sides(sequence)) == 6

def test_extract_subsection_sides_invalid_input():
    with pytest.raises(ValueError):
        Tile.extract_subsection_sides([0])

    with pytest.raises(ValueError):
        Tile.extract_subsection_sides([0, "h", "g", 1, 2, 3])

def test_is_valid_side_sequence():
    for type in SideType.all_types():
        assert Tile.is_valid_side_sequence(type.value)
        assert Tile.is_valid_side_sequence(type.value*6)

    for i in range(1, 10):
        if i == 1 or i == 6:
            assert Tile.is_valid_side_sequence(get_example_side_sequence(i))
        else:
            assert not Tile.is_valid_side_sequence(get_example_side_sequence(i))

    assert not Tile.is_valid_side_sequence("some gargabe")

    assert not Tile.is_valid_side_sequence(None)
    # valid length, but invalid char(s)
    assert not Tile.is_valid_side_sequence("ü")
    assert not Tile.is_valid_side_sequence("abcdef")

    # single type in isolating brackets should be ignored
    assert Tile.is_valid_side_sequence(f"{SideType.CROPS.value}")
    assert Tile.is_valid_side_sequence(f"({SideType.CROPS.value})")

    # use of isolating brackets
    example_sequence = get_example_side_sequence(6)
    for i in range(6):
        isolated_sequence = example_sequence[:i] + "(" + example_sequence[i] + ")" + example_sequence[i+1:]
        print(isolated_sequence)
        assert Tile.is_valid_side_sequence(isolated_sequence)

    # same type for an isolated side type
    sequence = "(" + get_sequence([SideType.WOODS, SideType.WOODS]) + ")"
    sequence += get_sequence([SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.CROPS])
    assert not Tile.is_valid_side_sequence(sequence)

def test_tile_rotation():

    tile_expected_rotated_sequences = [
        ([SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN],
         [[SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN],
          [SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS],
          [SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE],
          [SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS],
          [SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS]]
        ),
        ([SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.CROPS, SideType.CROPS],
         [[SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.GREEN],
          [SideType.CROPS, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.CROPS]]
        )
    ]

    for sequence, expected_rotated_sequences in tile_expected_rotated_sequences:
        tile = Tile(side_types=sequence, center_type=SideType.GREEN, coordinates=(0,0))

        rotated_tiles = tile.get_rotations()
        assert len(rotated_tiles) == len(expected_rotated_sequences)

        actual_rotated_sequences =[[side.type for side in rotated_tile.get_sides().values()] for rotated_tile in rotated_tiles]
        assert sequence not in actual_rotated_sequences

        for i in range(len(expected_rotated_sequences)):
            assert expected_rotated_sequences[i] == actual_rotated_sequences[i]

def test_tile_rotation_isolated():

    tile_expected_rotated_sequences = [
        (get_sequence([SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN], 1),
         [get_sequence([SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN], 0),
          get_sequence([SideType.HOUSE, SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS], 5),
          get_sequence([SideType.CROPS, SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE], 4),
          get_sequence([SideType.PONDS, SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS], 3),
          get_sequence([SideType.TRAIN, SideType.GREEN, SideType.WOODS, SideType.HOUSE, SideType.CROPS, SideType.PONDS], 2)]
        )
    ]

    for sequence, expected_rotated_sequences in tile_expected_rotated_sequences:
        tile = Tile(side_types=sequence, center_type=SideType.GREEN, coordinates=(0,0))

        rotated_tiles = tile.get_rotations()
        assert len(rotated_tiles) == len(expected_rotated_sequences)

        actual_rotated_sequences = [rotated_tile.get_side_type_seq() for rotated_tile in rotated_tiles]
        assert sequence not in actual_rotated_sequences

        for i in range(len(expected_rotated_sequences)):
            assert expected_rotated_sequences[i] == actual_rotated_sequences[i]

def test_eq():
    tile_0 = Tile(side_types=[SideType.GREEN], center_type=SideType.GREEN, coordinates=(0,0))
    tile_1 = Tile(side_types=[SideType.GREEN], center_type=SideType.GREEN, coordinates=(0,0))
    tile_2 = Tile(side_types=[SideType.GREEN], center_type=SideType.WOODS, coordinates=(0,0))
    tile_3 = Tile(side_types=[SideType.GREEN], center_type=SideType.GREEN, coordinates=(0,4))
    tile_4 = Tile(side_types=[SideType.WOODS], center_type=SideType.GREEN, coordinates=(0,0))

    assert tile_0 == tile_1
    assert tile_0 != tile_2
    assert tile_0 != tile_3
    assert tile_0 != tile_4

    # different types
    assert tile_0 != SideType.GREEN

def test_lt():
    tiles = [
        Tile(side_types=[SideType.GREEN], center_type=SideType.GREEN, coordinates=(0,4)),
        Tile(side_types=[SideType.GREEN], center_type=SideType.GREEN, coordinates=(-3,2)),
        Tile(side_types=[SideType.GREEN], center_type=SideType.WOODS, coordinates=(3,-8)),
        Tile(side_types=[SideType.GREEN], center_type=SideType.WOODS, coordinates=(0,0))
    ]

    expected_sorted_coordinates = [
        (-3,2),
        (0,0),
        (0,4),
        (3,-8)
    ]

    assert [tile.coordinates for tile in sorted(tiles)] == expected_sorted_coordinates

def test_get_coordinates():
    expected_coordinates = {
        TileSubsection.TOP: (0, 4),
        TileSubsection.UPPER_RIGHT: (3, 2),
        TileSubsection.LOWER_RIGHT: (3, -2),
        TileSubsection.BOTTOM: (0, -4),
        TileSubsection.LOWER_LEFT: (-3, -2),
        TileSubsection.UPPER_LEFT: (-3, +2),
        TileSubsection.CENTER: (0, 0)
    }

    for subsection in TileSubsection.get_all_values():
        actual_coords = Tile.get_coordinates((0,0), subsection)
        assert actual_coords == expected_coordinates[subsection]

def test_get_opposing():
    expected_opposites = {
        TileSubsection.TOP: TileSubsection.BOTTOM,
        TileSubsection.UPPER_RIGHT: TileSubsection.LOWER_LEFT,
        TileSubsection.LOWER_RIGHT: TileSubsection.UPPER_LEFT,
        TileSubsection.BOTTOM: TileSubsection.TOP,
        TileSubsection.LOWER_LEFT: TileSubsection.UPPER_RIGHT,
        TileSubsection.UPPER_LEFT: TileSubsection.LOWER_RIGHT,
        TileSubsection.CENTER: None
    }

    for subsection in TileSubsection.get_all_values():
        actual_opposite = Tile.get_opposing(subsection)
        assert actual_opposite == expected_opposites[subsection]

def test_get_direct_neighbors():
    expected_direct_neighbors = {
        TileSubsection.TOP: [TileSubsection.UPPER_LEFT, TileSubsection.UPPER_RIGHT],
        TileSubsection.UPPER_RIGHT: [TileSubsection.LOWER_RIGHT, TileSubsection.TOP],
        TileSubsection.LOWER_RIGHT: [TileSubsection.BOTTOM, TileSubsection.UPPER_RIGHT],
        TileSubsection.BOTTOM: [TileSubsection.LOWER_LEFT, TileSubsection.LOWER_RIGHT],
        TileSubsection.LOWER_LEFT: [TileSubsection.UPPER_LEFT, TileSubsection.BOTTOM],
        TileSubsection.UPPER_LEFT: [TileSubsection.TOP, TileSubsection.LOWER_LEFT],
        TileSubsection.CENTER: []
    }

    for subsection in TileSubsection.get_all_values():
        actual_direct_neighbors = Tile.get_direct_neighbors(subsection)
        assert sorted(actual_direct_neighbors) == sorted(expected_direct_neighbors[subsection])

def test_get_placement_considering_neighbor_tile():
    session = Session()
    session.load_from_csv("./tests/data/perfectly_closed_neighbor.csv", simulate_tile_placement=False)

    candidate = session.prepare_candidate([SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.GREEN],
                                           SideType.WOODS, coordinates=(3,2))

    assert session.played_tiles[(0,0)].get_placement() == Tile.Placement.PERFECT
    assert session.played_tiles[(0,0)].get_placement_considering_neighbor_tile(candidate) == Tile.Placement.IMPERFECT

    assert session.played_tiles[(0,4)].get_placement() == Tile.Placement.PERFECT
    assert session.played_tiles[(0,4)].get_placement_considering_neighbor_tile(candidate) == Tile.Placement.PERFECTLY_CLOSED

    assert session.played_tiles[(3,-2)].get_placement() == Tile.Placement.IMPERFECT
    assert session.played_tiles[(3,-2)].get_placement_considering_neighbor_tile(candidate) == Tile.Placement.IMPERFECT

def test_get_side_type_seq():
    example_sequence = \
        get_sequence([SideType.WOODS, SideType.HOUSE, SideType.WOODS, SideType.CROPS, SideType.WOODS, SideType.GREEN])
    for i in range(6):
        isolated_sequence = example_sequence[:i] + "(" + example_sequence[i] + ")" + example_sequence[i+1:]
        tile = Tile(side_types=isolated_sequence, center_type=SideType.GREEN, coordinates=None)
        assert tile.get_side_type_seq() == isolated_sequence