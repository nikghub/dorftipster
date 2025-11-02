import copy

from src.side_type import SideType
from src.tile_subsection import TileSubsection
from src.tile import Tile
from src.session import Session
from src.group import Group
from src.tile_evaluation import TileEvaluation

from tests.utils import get_sequence

def assert_group_expectation(actual_groups, group_expetations):
    assert len(actual_groups) == len(group_expetations)
    sorted_actual_groups = sorted([group for group in actual_groups.values()],
                                  key=lambda group: group.start_tile.coordinates)
    sorted_expected_groups = sorted(group_expetations, key=lambda e: e[5])

    for i, group in enumerate(sorted_actual_groups):
        start_tile_coords_e, initial_size_e, size_e, type_e, possible_extensions_e, coordinates_e = sorted_expected_groups[i]
        assert type_e == group.type
        assert initial_size_e == len(group.start_tile_subsections)
        assert start_tile_coords_e == group.start_tile.coordinates
        assert size_e == group.size

        assert sorted(coordinates_e) == sorted(group.tile_coordinates)

        sorted_actual_extension = sorted({coord: sorted(subsections)
                                          for coord, subsections in group.possible_extensions.items()
                                          }.items())
        sorted_expected_extension = sorted({coord: sorted(subsections)
                                            for coord, subsections in possible_extensions_e.items()
                                            }.items())
        assert sorted_expected_extension == sorted_actual_extension

def test_init():
    tile = Tile([SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN],
                SideType.CROPS, (0,0))
    group_type = SideType.CROPS
    subsections = [sub for sub in TileSubsection.get_all_values() if tile.get_side(sub).type == group_type]
    group = Group(tile, group_type, subsections)

    assert group.start_tile.coordinates == tile.coordinates
    assert group.start_tile_subsections == subsections
    assert group.type == group_type
    assert tile.coordinates in group.tile_coordinates
    assert group.size == len(subsections)

    expected_possible_extensions = {
        (0,4) : [TileSubsection.BOTTOM],
        (3,2) : [TileSubsection.LOWER_LEFT],
        (3,-2) : [TileSubsection.UPPER_LEFT],
        (0,-4) : [TileSubsection.TOP],
        (-3,-2) : [TileSubsection.UPPER_RIGHT],
        (-3,2) : [TileSubsection.LOWER_RIGHT],
    }
    assert sorted(group.possible_extensions) == sorted(expected_possible_extensions)
    assert group.id and len(group.id) == 8

def test_eq():
    session = Session()
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, (0,0)))
    session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, (0,4)))
    session.place_candidate(session.prepare_candidate([SideType.HOUSE], SideType.HOUSE, (3,2)))
    session.place_candidate(session.prepare_candidate([SideType.CROPS], SideType.CROPS, (3,-2)))
    session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, (0,-4)))
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, (-3,-2)))
    session.place_candidate(session.prepare_candidate([SideType.PONDS], SideType.PONDS, (-3,2)))

    assert len(session.groups) == 5

    for i, group_i in enumerate(session.groups.values()):
        for j, group_j in enumerate(session.groups.values()):
            if i == j:
                assert group_i == group_j
            else:
                assert group_i != group_j

        # different types
        assert group_i != 10
        assert group_i != "string"


def test_lt():
    groups = [
        Group(start_tile=Tile([SideType.WOODS], SideType.WOODS, (0,4)), side_type=SideType.WOODS, subsections=TileSubsection.get_all_values()),
        Group(start_tile=Tile([SideType.HOUSE], SideType.HOUSE, (3,2)), side_type=SideType.HOUSE, subsections=TileSubsection.get_all_values()),
        Group(start_tile=Tile([SideType.CROPS], SideType.CROPS, (3,-2)), side_type=SideType.CROPS, subsections=TileSubsection.get_all_values()),
        Group(start_tile=Tile([SideType.PONDS], SideType.PONDS, (0,-4)), side_type=SideType.PONDS, subsections=TileSubsection.get_all_values()),
        Group(start_tile=Tile([SideType.RIVER], SideType.RIVER, (-3,-2)), side_type=SideType.RIVER, subsections=TileSubsection.get_all_values()),
        Group(start_tile=Tile([SideType.TRAIN], SideType.TRAIN, (-3,2)), side_type=SideType.TRAIN, subsections=TileSubsection.get_all_values())
    ]

    sorted_groups = sorted(groups)
    assert sorted_groups != groups

    expected_order = [
        (-3,-2),
        (-3,2),
        (0,-4),
        (0,4),
        (3,-2),
        (3,2)
    ]

    assert all([a == b for a, b in zip(expected_order, [g.start_tile.coordinates for g in sorted_groups])])

def test_group_computation():
    session = Session()
    session.load_from_csv("./tests/data/group.csv", simulate_tile_placement=False)

    assert len(session.groups) == 3

    group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 4, 34, SideType.WOODS, {
                (3,6) : [TileSubsection.UPPER_LEFT],
                (3,-6) : [TileSubsection.TOP],
                (3,-14) : [TileSubsection.TOP],
                (6,-12) : [TileSubsection.TOP, TileSubsection.UPPER_LEFT],
                (9,-2) : [TileSubsection.LOWER_LEFT]
                },
                # all except for the tile at coordinate (-3,-2) connect to the group
                [tile.coordinates for tile in session.played_tiles.values() if tile.coordinates != (-3,-2)]
        ),
        ((3,10), 1, 1, SideType.WOODS, {
                (6,12) : [TileSubsection.LOWER_LEFT]
                },
                [(3,10)]
        ),
        ((-3,-2), 2, 2, SideType.WOODS, {
                (-6,0) : [TileSubsection.LOWER_RIGHT],
                (-6,-4) : [TileSubsection.UPPER_RIGHT]
                },
                [(-3,-2)]
        )
    ]

    assert_group_expectation(session.groups, group_expectation)

def test_group_connecting_tile():
    session = Session()
    session.load_from_csv("./tests/data/group_open.csv", simulate_tile_placement=False)

    expected_group_size_before_place = 52

    assert len(session.groups) == 1
    id, group = next(iter(session.groups.items()))
    assert SideType.WOODS == group.type
    assert 4 == len(group.start_tile_subsections)
    assert session.played_tiles[(0,0)].coordinates == group.start_tile.coordinates
    assert group.id == id
    assert expected_group_size_before_place == group.size

    # at coordinate (9, -2) we expect to be able to connect to the group at two tile subsections
    connecting_coordinate = (9, -2)
    assert connecting_coordinate in group.possible_extensions
    assert sorted([TileSubsection.LOWER_LEFT, TileSubsection.LOWER_RIGHT]) == group.possible_extensions[connecting_coordinate]

    candidate_tile_group_participation_expectations = [
        (session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN],
                                   SideType.GREEN, coordinates=connecting_coordinate),
         0),  # no connection
        (session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.GREEN],
                                   SideType.GREEN, coordinates=connecting_coordinate),
         1),  # left connected
        (session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN],
                                   SideType.GREEN, coordinates=connecting_coordinate),
         1),  # right connected
        (session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN],
                                   SideType.GREEN, coordinates=connecting_coordinate),
         2),  # left and right connected
        (session.prepare_candidate([SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.WOODS],
                                   SideType.GREEN, coordinates=connecting_coordinate),
         4),  # left and right connected (two subsections each)
        (session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN],
                                   SideType.WOODS, coordinates=connecting_coordinate),
         3)  # through connected
    ]

    for candidate_tile, expectation in candidate_tile_group_participation_expectations:
        # test for prepared candidate
        if expectation > 0:
            assert group.id in candidate_tile.group_participation
            assert len(candidate_tile.group_participation[group.id].subsections) == expectation
        else:
            assert group.id not in candidate_tile.group_participation

        assert expected_group_size_before_place == group.size
        session.place_candidate(candidate_tile)

        # test for placed tile after recomputation of group
        assert group.size == expected_group_size_before_place + expectation
        if expectation > 0:
            assert len(candidate_tile.group_participation[group.id].subsections) == expectation
        else:
            assert group.id not in candidate_tile.group_participation

        session.undo_last_tile()

def test_group_candidate():
    session = Session()
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, (0,0)))
    session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, (0,4)))

    assert len(session.groups) == 1
    group = list(session.groups.values())[0]

    candidates = [
        session.prepare_candidate([SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.WOODS], SideType.GREEN, (3,2)),
        session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS], SideType.GREEN, (3,2))
    ]

    for i, candidate in enumerate(candidates):
        print(i)
        assert len(candidate.group_participation) == 2
        assert group.id in candidate.group_participation
        assert len(candidate.group_participation[group.id].subsections) > 0

    assert sorted(candidates[0].group_participation[group.id].subsections) == sorted([TileSubsection.TOP, TileSubsection.UPPER_LEFT])
    assert sorted(candidates[1].group_participation[group.id].subsections) == sorted([TileSubsection.UPPER_LEFT])

def test_group_extension():
    session = Session()
    session.load_from_csv("./tests/data/group_expansion.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 7, 7, SideType.HOUSE, {
                (0,4) : [TileSubsection.BOTTOM],
                (3,-2) : [TileSubsection.UPPER_LEFT],
                (0,-4) : [TileSubsection.TOP],
                (-3,-2) : [TileSubsection.UPPER_RIGHT]
                },
                [(0,0)]
        ),
        ((-3,2), 7, 7, SideType.WOODS, {
                (-3,6) : [TileSubsection.BOTTOM],
                (0,4) : [TileSubsection.LOWER_LEFT],
                (-3,-2) : [TileSubsection.TOP],
                (-6,0) : [TileSubsection.UPPER_RIGHT],
                (-6,4) : [TileSubsection.LOWER_RIGHT]
                },
                [(-3,2)]
        ),
        ((3,2), 7, 7, SideType.CROPS, {
                (3,6) : [TileSubsection.BOTTOM],
                (6,4) : [TileSubsection.LOWER_LEFT],
                (6,0) : [TileSubsection.UPPER_LEFT],
                (3,-2) : [TileSubsection.TOP],
                (0,4) : [TileSubsection.LOWER_RIGHT]
                },
                [(3,2)]
        )
    ]

    assert_group_expectation(session.groups, initial_group_expectation)

    # place a tile that extends the house and crops group and opens another house group
    new_tile = session.prepare_candidate([SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.HOUSE, SideType.GREEN, SideType.GREEN],
                                         SideType.WOODS,
                                         (0,4))

    session.place_candidate(new_tile)

    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 7, 8, SideType.HOUSE, {
                (3,-2) : [TileSubsection.UPPER_LEFT],
                (0,-4) : [TileSubsection.TOP],
                (-3,-2) : [TileSubsection.UPPER_RIGHT]
                },
                [(0,0),(0,4)]
        ),
        ((-3,2), 7, 7, SideType.WOODS, {
                (-3,6) : [TileSubsection.BOTTOM],
                (-3,-2) : [TileSubsection.TOP],
                (-6,0) : [TileSubsection.UPPER_RIGHT],
                (-6,4) : [TileSubsection.LOWER_RIGHT]
                },
                [(-3,2)]
        ),
        ((3,2), 7, 9, SideType.CROPS, {
                (3,6) : [TileSubsection.BOTTOM, TileSubsection.LOWER_LEFT],
                (6,4) : [TileSubsection.LOWER_LEFT],
                (6,0) : [TileSubsection.UPPER_LEFT],
                (3,-2) : [TileSubsection.TOP]
                },
                [(3,2),(0,4)]
        ),
        ((0,4), 1, 1, SideType.HOUSE, {
                (0,8) : [TileSubsection.BOTTOM]
                },
                [(0,4)]
        )
    ]

    assert_group_expectation(session.groups, after_place_group_expectation)

    for i, group in enumerate(session.groups.values()):
        initial_size_e, size_e = after_place_group_expectation[i][1:3]

        # existing group participation
        if (group_participation_e := size_e - initial_size_e) > 0:
            assert group.id in new_tile.group_participation
            assert len(new_tile.group_participation[group.id].subsections) == group_participation_e
        # new group
        elif new_tile.coordinates == group.start_tile.coordinates:
            assert group.id in new_tile.group_participation
            assert len(new_tile.group_participation[group.id].subsections) == size_e
        # no participation
        else:
            assert group.id not in new_tile.group_participation

def test_group_merge():
    session = Session()
    session.load_from_csv("./tests/data/group_merge.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 3, 3, SideType.WOODS, {
                (-3,-2) : [TileSubsection.UPPER_RIGHT],
                (3,-2) : [TileSubsection.UPPER_LEFT]
                },
                [(0,0)]
        ),
        ((0,-4), 3, 3, SideType.WOODS, {
                (3,-2) : [TileSubsection.LOWER_LEFT],
                (0,-8) : [TileSubsection.TOP]
                },
                [(0,-4)]
        ),
        ((3,2), 1, 6, SideType.WOODS, {
                (3,-2) : [TileSubsection.UPPER_RIGHT]
                },
                [(3,2),(6,0),(6,-4)]
        ),
        ((3,-6), 3, 3, SideType.HOUSE, {
                (3,-2) : [TileSubsection.BOTTOM],
                (3,-10) : [TileSubsection.TOP],
                },
                [(3,-6)]
        ),
        ((6,-4), 1, 1, SideType.HOUSE, {
                (3,-2) : [TileSubsection.LOWER_RIGHT]
                },
                [(6,-4)]
        )
    ]
    # we expect the groups to be merged after placing the tile
    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 3, 17, SideType.WOODS, {
                (-3,-2) : [TileSubsection.UPPER_RIGHT],
                (0,-8) : [TileSubsection.TOP]
                },
                [(0,0),(0,-4),(3,-2),(3,2),(6,0),(6,-4)]
        ),
        ((3,-6), 3, 6, SideType.HOUSE, {
                (3,-10) : [TileSubsection.TOP]
                },
                [(3,-6),(6,-4),(3,-2)]
        )
    ]
    connecting_tile_coords = (3,-2)

    assert len(session.groups) == 5
    woods_group_ids = [g.id for g in session.groups.values() if g.type == SideType.WOODS]
    houses_group_ids = [g.id for g in session.groups.values() if g.type == SideType.HOUSE]

    def assert_initial(actual_groups):
        assert_group_expectation(actual_groups, initial_group_expectation)
        assert len(actual_groups) == len(initial_group_expectation)
        for g_id in woods_group_ids:
            assert g_id in actual_groups
        for g_id in houses_group_ids:
            assert g_id in actual_groups

    def assert_initial_marked_for_deletion():
        assert len(session.groups_marked_for_deletion_at_coords) == 0

    def assert_after_place(actual_groups):
        assert_group_expectation(actual_groups, after_place_group_expectation)
        assert len(actual_groups) == len(after_place_group_expectation)

        # verify only first group was kept
        assert woods_group_ids[0] in actual_groups
        assert houses_group_ids[0] in actual_groups
        for g_id in woods_group_ids[1:]:
            assert g_id not in actual_groups
        for g_id in houses_group_ids[1:]:
            assert g_id not in actual_groups

    def assert_after_place_marked_for_deletion():
        assert len(session.groups_marked_for_deletion_at_coords) == 1
        assert connecting_tile_coords in session.groups_marked_for_deletion_at_coords
        assert len(session.groups_marked_for_deletion_at_coords[connecting_tile_coords]) == 3
        group_ids_marked_for_deletion =\
            [group.id for group in session.groups_marked_for_deletion_at_coords[connecting_tile_coords]]
        assert woods_group_ids[0] not in group_ids_marked_for_deletion
        assert houses_group_ids[0] not in group_ids_marked_for_deletion
        for g_id in woods_group_ids[1:]:
            assert g_id in group_ids_marked_for_deletion
        for g_id in houses_group_ids[1:]:
            assert g_id in group_ids_marked_for_deletion

    def prepare_candidate():
        # prepare a tile that connects the groups at (3,-2)
        return session.prepare_candidate([SideType.WOODS, SideType.WOODS, SideType.HOUSE, SideType.HOUSE, SideType.WOODS, SideType.WOODS],
                                         SideType.WOODS,
                                         connecting_tile_coords)

    assert_initial(session.groups)
    assert_initial_marked_for_deletion()

    # verify that the prepared candidate already reflects the new state that would occur after place
    new_tile = prepare_candidate()
    assert_after_place({gp.group.id: gp.group for gp in new_tile.group_participation.values()})

    session.place_candidate(new_tile)
    assert_after_place(session.groups)
    assert_after_place_marked_for_deletion()

    # when undoing the last tile, we expect to see the initial expectation again
    session.undo_last_tile()
    assert_initial(session.groups)
    assert_initial_marked_for_deletion()

    # place again
    session.place_candidate(prepare_candidate())
    assert_after_place(session.groups)
    assert_after_place_marked_for_deletion()

    # place any other tile to verify that the group connection information (including merged groups) is garbage collected
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, (0,4)))

    assert len(session.groups) == 2
    assert woods_group_ids[0] in session.groups
    assert houses_group_ids[0] in session.groups
    assert len(session.groups_marked_for_deletion_at_coords) == 0

def test_group_closed():
    session = Session()
    session.load_from_csv("./tests/data/group_almost_closed.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 3, 10, SideType.WOODS, {
                (-3,-2) : [TileSubsection.UPPER_RIGHT, TileSubsection.LOWER_RIGHT]
                },
                [(0,0),(0,-4),(3,-2),(0,-8)]),
        ((3,-2), 1, 1, SideType.HOUSE, {
                (6,0) : [TileSubsection.LOWER_LEFT]
                },
                [(3,-2)])
        ]
    after_first_place_group_expectation = [
        ((3,-2), 1, 1, SideType.HOUSE, {
                (6,0) : [TileSubsection.LOWER_LEFT]
                },
                [(3,-2)])
    ]
    after_second_place_group_expectation = []

    assert len(session.groups) == 2
    first_group = list(session.groups.values())[0]
    second_group = list(session.groups.values())[1]

    def assert_initial():
        assert_group_expectation(session.groups, initial_group_expectation)
        assert first_group.id in session.groups
        assert second_group.id in session.groups
        assert len(session.groups_marked_for_deletion_at_coords) == 0

    def assert_after_place(group_expectation, relevant_group, tile_coords):
        assert_group_expectation(session.groups, group_expectation)
        assert relevant_group.id not in session.groups
        assert len(session.groups_marked_for_deletion_at_coords) == 1
        assert tile_coords in session.groups_marked_for_deletion_at_coords
        assert relevant_group.id in [group.id for group in session.groups_marked_for_deletion_at_coords[tile_coords]]

    assert_initial()

    # place a tile that closes the first group
    first_closing_tile_coords = (-3,-2)
    new_tile = session.prepare_candidate([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN],
                                         SideType.GREEN,
                                         first_closing_tile_coords)
    # ensure that the group is deleted
    session.place_candidate(new_tile)
    assert_after_place(after_first_place_group_expectation, first_group, first_closing_tile_coords)

    # verify that undo restores the original state
    session.undo_last_tile()
    assert_initial()

    # place again
    session.place_candidate(new_tile)
    assert_after_place(after_first_place_group_expectation, first_group, first_closing_tile_coords)

    # place a tile that closes the second group and verify first group is garbage collected
    second_closing_tile_coords = (6,0)
    new_tile = session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.HOUSE, SideType.GREEN],
                                         SideType.GREEN,
                                         second_closing_tile_coords)
    session.place_candidate(new_tile)
    assert_after_place(after_second_place_group_expectation, second_group, second_closing_tile_coords)

    # place any other tile to verify that the second closed group will be garbage collected
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, (0,4)))

    assert len(session.groups) == 0
    assert len(session.groups_marked_for_deletion_at_coords) == 0

def test_group_merge_and_close():
    session = Session()
    session.load_from_csv("./tests/data/group_close_and_merge.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,0), 3, 4, SideType.WOODS, {
                (3,-2) : [TileSubsection.UPPER_LEFT]
                },
                [(0,0),(-3,-2)]),
        ((0,-4), 3, 4, SideType.WOODS, {
                (3,-2) : [TileSubsection.LOWER_LEFT]
                },
                [(0,-4),(0,-8)]),
        ((6,-4), 1, 1, SideType.HOUSE, {
                (3,-2) : [TileSubsection.LOWER_RIGHT]
                },
                [(6,-4)]),
        ((3,-6), 1, 1, SideType.CROPS, {
                (3,-2) : [TileSubsection.BOTTOM]
                },
                [(3,-6)]),
        ((6,0), 3, 27, SideType.RIVER, {
                (3,-2) : [TileSubsection.UPPER_RIGHT],
                (3,6) : [TileSubsection.LOWER_RIGHT],
                (12,0) : [TileSubsection.UPPER_LEFT, TileSubsection.TOP],
                (6,12) : [TileSubsection.BOTTOM]
                },
                [(6,0),(9,2),(12,4),(6,4),(6,8)]),
        ((9,6), 3, 20, SideType.TRAIN, {
                (3,-2) : [TileSubsection.TOP],
                (3,6) : [TileSubsection.LOWER_RIGHT],
                (12,0) : [TileSubsection.TOP]
                },
                [(9,6),(12,4),(6,4),(3,2)])
        ]

    assert_group_expectation(session.groups, initial_group_expectation)

    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((6,0), 3, 28, SideType.RIVER, {
                (3,6) : [TileSubsection.LOWER_RIGHT],
                (12,0) : [TileSubsection.UPPER_LEFT, TileSubsection.TOP],
                (6,12) : [TileSubsection.BOTTOM]
                },
                [(6,0),(9,2),(12,4),(6,4),(6,8),(3,-2)]),
        ((9,6), 3, 22, SideType.TRAIN, {
                (3,6) : [TileSubsection.LOWER_RIGHT],
                (12,0) : [TileSubsection.TOP]
                },
                [(9,6),(12,4),(6,4),(3,2),(3,-2)])
        ]

    new_tile_coords = (3,-2)
    new_tile = session.prepare_candidate([SideType.TRAIN, SideType.RIVER, SideType.GREEN, SideType.CROPS, SideType.WOODS, SideType.WOODS],
                                          SideType.TRAIN,
                                          new_tile_coords)

    # tile will merge and close the woods groups, will close the house and crops group and will extend the train and river groups
    session.place_candidate(new_tile)
    assert_group_expectation(session.groups, after_place_group_expectation)

    # verify that we are able to restore the initial state if tile is undone
    session.undo_last_tile()
    assert_group_expectation(session.groups, initial_group_expectation)

    # verify that placing again has no side-effects and restores the same state
    session.place_candidate(new_tile)
    assert_group_expectation(session.groups, after_place_group_expectation)

def test_group_merge_river_ponds():
    session = Session()
    session.load_from_csv("./tests/data/group_river_ponds_merge.csv", simulate_tile_placement=False)

    initial_group_state = copy.deepcopy(session.groups)

    def prepare_candidate():
        # the tile connects a river group with a ponds group and we want to ensure that these are merged
        connecting_tile_coords = (-27,-26)
        return session.prepare_candidate([SideType.RIVER, SideType.RIVER, SideType.GREEN, SideType.RIVER, SideType.RIVER, SideType.GREEN],
                                         SideType.RIVER,
                                         connecting_tile_coords)

    def assert_initial():
        assert len(session.groups) == 68
        assert session.groups == initial_group_state

    def assert_after_place():
        assert len(session.groups) == 67

    assert_initial()

    session.place_candidate(prepare_candidate())
    assert_after_place()

    session.undo_last_tile()
    assert_initial()

    session.place_candidate(prepare_candidate())
    assert_after_place()

def test_group_merge_ponds_river():
    session = Session()
    session.load_from_csv("./tests/data/group_ponds_river_merge.csv", simulate_tile_placement=False)

    initial_group_state = copy.deepcopy(session.groups)

    def prepare_candidate():
        # the tile connects a ponds group with a river group and we want to ensure that these are merged
        connecting_tile_coords = (-27,-26)
        return session.prepare_candidate([SideType.RIVER, SideType.RIVER, SideType.GREEN, SideType.RIVER, SideType.RIVER, SideType.GREEN],
                                          SideType.RIVER,
                                          connecting_tile_coords)

    def assert_initial():
        assert len(session.groups) == 67
        assert session.groups == initial_group_state

    def assert_after_place():
        assert len(session.groups) == 66

    assert_initial()

    session.place_candidate(prepare_candidate())
    assert_after_place()

    session.undo_last_tile()
    assert_initial()

    session.place_candidate(prepare_candidate())
    assert_after_place()

def test_river_ponds_train_station_compatibility():
    session = Session()
    session.load_from_csv("./tests/data/group_river_ponds_train_station.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 7, SideType.PONDS, {
                (3,2) : [TileSubsection.UPPER_LEFT]
                },
                [(0,4)]),
        ((-3,-2), 3, 4, SideType.TRAIN, {
                (0,-4) : [TileSubsection.UPPER_LEFT]
                },
                [(-3,-2), (-6,0)]),
        ((9, -2), 3, 4, SideType.RIVER, {
                (6,-4) : [TileSubsection.UPPER_RIGHT]
                },
                [(9,-2), (12, 0)])
        ]

    assert_group_expectation(session.groups, initial_group_expectation)

    new_tile_coords = (3,2)
    new_tile = session.prepare_candidate([SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS],
                                          SideType.PONDS,
                                          new_tile_coords)
    session.place_candidate(new_tile)
    after_connect_ponds_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 19, SideType.PONDS, {
                (6,-4) : [TileSubsection.UPPER_LEFT],
                (3,-6) : [TileSubsection.TOP],
                (0,-4) : [TileSubsection.UPPER_RIGHT]
                },
                [(0,4), (3,2), (3,-2)]),
        ((-3,-2), 3, 4, SideType.TRAIN, {
                (0,-4) : [TileSubsection.UPPER_LEFT]
                },
                [(-3,-2), (-6,0)]),
        ((9,-2), 3, 4, SideType.RIVER, {
                (6,-4) : [TileSubsection.UPPER_RIGHT]
                },
                [(9,-2), (12, 0)])
        ]
    assert_group_expectation(session.groups, after_connect_ponds_group_expectation)

    new_tile_coords = (0,-4)
    new_tile = session.prepare_candidate([SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.TRAIN],
                                          SideType.TRAIN,
                                          new_tile_coords)
    session.place_candidate(new_tile)
    after_connect_train_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 19, SideType.PONDS, {
                (6,-4) : [TileSubsection.UPPER_LEFT],
                (3,-6) : [TileSubsection.TOP]
                },
                [(0,4), (3,2), (3, -2)]),
        ((-3,-2), 3, 14, SideType.TRAIN, {
                (6,-4) : [TileSubsection.UPPER_LEFT],
                (3,-6) : [TileSubsection.TOP]
                },
                [(-3,-2), (-6,0), (0,-4), (3, -2)]),
        ((9,-2), 3, 4, SideType.RIVER, {
                (6,-4) : [TileSubsection.UPPER_RIGHT]
                },
                [(9,-2), (12, 0)])
        ]
    assert_group_expectation(session.groups, after_connect_train_group_expectation)

    new_tile_coords = (6,-4)
    new_tile = session.prepare_candidate([SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.RIVER],
                                          SideType.RIVER,
                                          new_tile_coords)
    session.place_candidate(new_tile)
    after_connect_river_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 26, SideType.PONDS, {
                (3,-6) : [TileSubsection.TOP]
                },
                [(0,4), (3,2), (3, -2), (9,-2), (12, 0), (6,-4)]),
        ((-3,-2), 3, 14, SideType.TRAIN, {
                (3,-6) : [TileSubsection.TOP]
                },
                [(-3,-2), (-6,0), (0,-4), (3, -2)])
        ]
    assert_group_expectation(session.groups, after_connect_river_group_expectation)

    new_tile_coords = (3,-6)
    new_tile = session.prepare_candidate([SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN],
                                          SideType.RIVER,
                                          new_tile_coords)
    session.place_candidate(new_tile)
    after_extend_ponds_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 29, SideType.PONDS, {
                (3,-10) : [TileSubsection.TOP]
                },
                [(0,4), (3,2), (3, -2), (9,-2), (12, 0), (6,-4), (3,-6)])
        ]
    assert_group_expectation(session.groups, after_extend_ponds_group_expectation)

def test_station_consideration():
    session = Session()
    session.load_from_csv("./tests/data/group_ponds_station.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 14, SideType.PONDS, {
                (3,2) : [TileSubsection.UPPER_LEFT, TileSubsection.TOP],
                (3,10) : [TileSubsection.BOTTOM]
                },
                [(0,4),(3,6)])
        ]

    assert_group_expectation(session.groups, initial_group_expectation)

    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,4), 7, 16, SideType.PONDS, {
                (3,10) : [TileSubsection.BOTTOM]
                },
                [(0,4),(3,6),(3,2)]),
        ((3,2), 2, 16, SideType.PONDS, {
                (0,-4) : [TileSubsection.UPPER_RIGHT],
                (3,-6) : [TileSubsection.TOP],
                (6,-4) : [TileSubsection.UPPER_LEFT, TileSubsection.TOP],
                (9,-2) : [TileSubsection.UPPER_LEFT],
                (9,2) : [TileSubsection.LOWER_LEFT]
                },
                [(3,2),(3,-2),(6,0)])
        ]

    new_tile = session.prepare_candidate([SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.GREEN],
                                         SideType.GREEN,
                                         (3,2))

    assert_group_expectation(session.groups, initial_group_expectation)
    assert_group_expectation({gp.group.id: gp.group for gp in new_tile.group_participation.values()}, after_place_group_expectation)

    session.place_candidate(new_tile)
    assert_group_expectation(session.groups, after_place_group_expectation)


def test_group_type_compatibility():
    def assert_group_at_index(groups, index, expected_size, expected_coordinates, expected_type):
        assert len(groups) > index
        group = list(groups.values())[index]
        assert group.type == expected_type
        assert group.size == expected_size
        assert len(group.tile_coordinates) == len(expected_coordinates)
        assert group.tile_coordinates == expected_coordinates

    session = Session()
    for first_tile_type in SideType.get_values():
        first_coord = (0,0)
        session.place_candidate(session.prepare_candidate([first_tile_type], first_tile_type, first_coord))

        if first_tile_type in Group.ALLOWED_GROUP_TYPES:
            # new group
            assert_group_at_index(groups=session.groups, index=0,
                                  expected_size=7, expected_coordinates=[first_coord], expected_type=first_tile_type)
        else:
            assert len(session.groups) == 0

        for second_tile_type in SideType.get_values():
            second_coord = (0,4)
            candidate = session.prepare_candidate([second_tile_type], second_tile_type, second_coord)

            if (second_tile_type in TileEvaluation.RESTRICTED_DICT and\
                first_tile_type not in TileEvaluation.RESTRICTED_DICT[second_tile_type])\
                or\
                (first_tile_type in TileEvaluation.RESTRICTED_DICT and\
                 second_tile_type not in TileEvaluation.RESTRICTED_DICT[first_tile_type]):
                assert candidate == None
                continue

            session.place_candidate(candidate)

            if first_tile_type in Group.ALLOWED_GROUP_TYPES:
                # extension of existing group
                if second_tile_type in Group.COMPATIBLE_GROUP_TYPES[first_tile_type]:
                    assert_group_at_index(groups=session.groups, index=0,
                                          expected_size=14, expected_coordinates=[first_coord, second_coord], expected_type=first_tile_type)
                # new group
                elif second_tile_type in Group.ALLOWED_GROUP_TYPES:
                    assert_group_at_index(groups=session.groups, index=0,
                                          expected_size=7, expected_coordinates=[first_coord], expected_type=first_tile_type)
                    assert_group_at_index(groups=session.groups, index=1,
                                          expected_size=7, expected_coordinates=[second_coord], expected_type=second_tile_type)
                # no additional group or extension of existing group
                else:
                    assert_group_at_index(groups=session.groups, index=0,
                                          expected_size=7, expected_coordinates=[first_coord], expected_type=first_tile_type)
            # new group
            elif second_tile_type in Group.ALLOWED_GROUP_TYPES:
                # ensure that we will pick up STATION as type which will not have created a new group by itself,
                # but should be considered a part of the new group that we create with an allowed group type
                if first_tile_type in Group.COMPATIBLE_GROUP_TYPES and second_tile_type in Group.COMPATIBLE_GROUP_TYPES[first_tile_type]:
                    assert_group_at_index(groups=session.groups, index=0,
                                          expected_size=14, expected_coordinates=[second_coord, first_coord], expected_type=second_tile_type)
                else:
                    assert_group_at_index(groups=session.groups, index=0,
                                          expected_size=7, expected_coordinates=[second_coord], expected_type=second_tile_type)
            else:
                assert len(session.groups) == 0

            session.undo_last_tile()

        session.undo_last_tile()

def test_group_connected_subsections():
    group_type = SideType.HOUSE

    session = Session()
    session.place_candidate(session.prepare_candidate([group_type], group_type, coordinates=(0,0)))

    assert len(session.groups) == 1
    group = next(iter(session.groups.values()))
    assert group.type == group_type

    # verify that we are building the tile participation correctly for
    for center in [SideType.GREEN, group_type]:
        for top in SideType.get_values():
            for ur in SideType.get_values():
                for lr in SideType.get_values():
                    for bot in SideType.get_values():
                        for ll in SideType.get_values():
                            for ul in SideType.get_values():
                                seq = [top, ur, lr, bot, ll, ul]
                                # as we always place the tile above (0,0), we will always connect at bottom of tile
                                tile = Tile(side_types=seq, center_type=center, coordinates=(0,4))
                                group_connecting_subsection = TileSubsection.BOTTOM
                                connected_subsections = group.get_group_connected_tile_subsections(tile, group_connecting_subsection)

                                # we can never connect if the connecting side is of a different type
                                if bot != group_type:
                                    assert len(connected_subsections) == 0
                                    continue

                                expected_size = 1  # bot

                                # through the center we may always reach all sides
                                if center == group_type:
                                    expected_size += 1
                                    expected_size += 1 if ll == group_type else 0
                                    expected_size += 1 if ul == group_type else 0
                                    expected_size += 1 if top == group_type else 0
                                    expected_size += 1 if ur == group_type else 0
                                    expected_size += 1 if lr == group_type else 0
                                # otherwise we may only hop from one side to the next
                                else:
                                    if lr != group_type and ll != group_type:
                                        pass  # no more connected subsections
                                    elif lr != group_type and ll == group_type:
                                        expected_size += 1  # lower left
                                        if ul == group_type:
                                            expected_size += 1  # upper left
                                            if top == group_type:
                                                expected_size += 1  # top
                                                if ur == group_type:
                                                    expected_size += 1  # upper right
                                    elif lr == group_type and ll != group_type:
                                        expected_size += 1  # lower right
                                        if ur == group_type:
                                            expected_size += 1  # upper right
                                            if top == group_type:
                                                expected_size += 1  # top
                                                if ul == group_type:
                                                    expected_size += 1  # upper left
                                    else:
                                        expected_size += 2  # lower left, lower right
                                        expected_size += 1 if ul == group_type else 0
                                        expected_size += 1 if ur == group_type else 0
                                        if (ul == group_type or ur == group_type) and top == group_type:
                                            expected_size += 1  # top

                                assert len(connected_subsections) == expected_size

                                # verify that the logic of both methods matches regarding grouping subsections
                                typed_subsections = [(type, subsections) for type, subsections in Group.get_connected_subsection_groups(tile)\
                                       if group_connecting_subsection in subsections]
                                assert len(typed_subsections) == 1
                                type, subsections = typed_subsections[0]
                                assert type == group_type
                                assert sorted(subsections) == sorted(connected_subsections)

def test_group_isolated_side():
    session = Session()
    session.load_from_csv("./tests/data/group_isolated_side.csv", simulate_tile_placement=False)

    initial_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((-3,-2), 4, 6, SideType.WOODS, {
                (0,-4) : [TileSubsection.UPPER_LEFT, TileSubsection.LOWER_LEFT]
                },
                [(-3,-2),(-3,-6)])
        ]

    ## -----
    assert_group_expectation(session.groups, initial_group_expectation)

    new_tile = session.prepare_candidate(
        get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 3),
        SideType.WOODS,
        (0,-4)
        )

    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((-3,-2), 4, 9, SideType.WOODS, {
                (3,-2) : [TileSubsection.LOWER_LEFT]
                },
                [(-3,-2),(-3,-6),(0,-4)]),
        ((0,-4), 1, 1, SideType.WOODS, {
                (0,-8) : [TileSubsection.TOP]
                },
                [(0,-4)])
        ]
    assert_group_expectation({gp.group.id: gp.group for gp in new_tile.group_participation.values()}, after_place_group_expectation)

    session.place_candidate(new_tile)
    assert_group_expectation(session.groups, after_place_group_expectation)


    ## -----
    session.undo_last_tile()
    new_tile = session.prepare_candidate(
        get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 5),
        SideType.WOODS,
        (0,-4)
        )

    group_participation_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((-3,-2), 4, 7, SideType.WOODS, {
                },
                [(-3,-2),(-3,-6),(0,-4)]),
        ((0,-4), 3, 3, SideType.WOODS, {
                (3,-2) : [TileSubsection.LOWER_LEFT],
                (0,-8) : [TileSubsection.TOP]
                },
                [(0,-4)])
        ]
    assert_group_expectation({gp.group.id: gp.group for gp in new_tile.group_participation.values()}, group_participation_expectation)

    session.place_candidate(new_tile)

    after_place_group_expectation = [
        # start tile, initial size, size, type, possible extensions, tile coordinates in group
        ((0,-4), 3, 3, SideType.WOODS, {
                (3,-2) : [TileSubsection.LOWER_LEFT],
                (0,-8) : [TileSubsection.TOP]
                },
                [(0,-4)])
        ]
    assert_group_expectation(session.groups, after_place_group_expectation)