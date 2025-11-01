import filecmp
import os
import pytest

import pandas as pd

from src.side import Side
from src.side_type import SideType
from src.session import Session
from src.tile import Tile
from src.tile_evaluation import TileEvaluation
from src.tile_subsection import TileSubsection
from src.constants import DatabaseConstants

def compute_sequence(side_types):
    return "".join(type.to_character() for type in side_types)

def assert_session_equal(left, right):
    assert len(left.played_tiles) == len(right.played_tiles)
    assert all([a == b for a, b in zip(left.played_tiles, right.played_tiles)])

    assert len(left.groups) == len(right.groups)
    assert all(a == b for a, b in zip(left.groups.values(), right.groups.values()))

def assert_session_not_equal(left, right):
    assert len(left.played_tiles) != len(right.played_tiles) or \
           any([a != b for a, b in zip(left.played_tiles, right.played_tiles)]) or\
           len(left.groups) == len(right.groups) or \
           any(a != b for a, b in zip(left.groups.values(), right.groups.values()))

def assert_watched_coords_equal(left, right):
    assert len(left.watched_open_coords) == len(right.watched_open_coords)
    assert all([a == b for a, b in zip(left.watched_open_coords, right.watched_open_coords)])

def test_session_start():
    session = Session()
    assert len(session.played_tiles) == 0

    session.start()
    assert len(session.played_tiles) == 1
    assert next(iter(session.played_tiles)) == (0,0)

def test_tile_place_invalid():
    session = Session()
    session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,0)))
    # coordinate already taken
    with pytest.raises(ValueError):
        session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, coordinates=(0,0)))

    # type restriction
    with pytest.raises(ValueError):
        session.place_candidate(session.prepare_candidate([SideType.RIVER], SideType.RIVER, coordinates=(0,4)))

    # None value
    with pytest.raises(ValueError):
        session.place_candidate(None)

def test_tile_place_undo():
    session = Session()
    start_tile = session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,0))
    session.place_candidate(start_tile)

    assert len(session.played_tiles) == 1
    assert start_tile.coordinates in session.played_tiles
    assert session.played_tiles[start_tile.coordinates] == start_tile

    candidates = session.compute_candidate_tiles(side_type_seq=SideType.GREEN.to_character(),
                                                 center_type=SideType.GREEN.to_character())
    assert len(candidates) == 6

    new_tile = candidates[0]

    session.place_candidate(new_tile)
    assert len(session.played_tiles) == 2
    assert new_tile.coordinates in session.played_tiles
    assert session.played_tiles[new_tile.coordinates] == new_tile

    session.undo_last_tile()
    assert len(session.played_tiles) == 1
    assert new_tile.coordinates not in session.played_tiles
    assert start_tile.coordinates in session.played_tiles
    assert session.played_tiles[start_tile.coordinates] == start_tile

def test_quest_tile_place_undo():
    session = Session()
    start_tile = session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,0))
    session.place_candidate(start_tile)

    assert len(session.groups) == 0

    sequence = compute_sequence([SideType.WOODS])
    candidates = session.compute_candidate_tiles(side_type_seq=sequence,
                                                 center_type=SideType.WOODS.to_character(),
                                                 quest_type=SideType.WOODS.to_character())
    assert len(candidates) == 6

    new_tile = candidates[0]

    session.place_candidate(new_tile)

    assert len(session.groups) == 1
    id, group = next(iter(session.groups.items()))
    assert group.start_tile.coordinates == new_tile.coordinates
    assert group.size > 0

    session.undo_last_tile()
    assert len(session.groups) == 0

def test_no_database():
    session = Session(database_name=None)
    session.start()

    with pytest.raises(RuntimeError):
        session.get_all_sessions_from_database()

    with pytest.raises(RuntimeError):
        session.save_to_database("some name")

    with pytest.raises(RuntimeError):
        session.load_from_database("some id", simulate_tile_placement=False)

    with pytest.raises(RuntimeError):
        session.delete_from_database("10")

    with pytest.raises(RuntimeError):
        session.autosave(list(session.played_tiles.values())[0])

def test_load_from_empty_database():
    database = "./tests/data/__test_empty_database__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with Session(database) as session:
        with pytest.raises(ValueError):
            session.load_from_database(0, simulate_tile_placement=False)

    os.remove(database)

def test_load_from_empty_csv():
    session = Session()
    with pytest.raises(ValueError):
        session.load_from_csv("./tests/data/empty_session.csv", simulate_tile_placement=False)

def test_csv_error_cases():
    session = Session()

    with pytest.raises(ValueError):
        session.save_to_csv(file_name=None)
    with pytest.raises(ValueError):
        session.save_to_csv(file_name="")

    with pytest.raises(ValueError):
        session.load_from_csv(file_name=None, simulate_tile_placement=False)
    with pytest.raises(ValueError):
        session.load_from_csv(file_name="", simulate_tile_placement=False)
    with pytest.raises(FileNotFoundError):
        session.load_from_csv(file_name="non existing file path", simulate_tile_placement=False)

def test_save_load_delete():
    database = "./tests/data/__test_save_load__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with Session(database) as session:
        session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,0)))
        session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, coordinates=(0,4)), quest_type=SideType.WOODS)
        session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.HOUSE, coordinates=(3,2)))
        session.place_candidate(session.prepare_candidate([SideType.CROPS], SideType.CROPS, coordinates=(3,-2)))
        session.place_candidate(session.prepare_candidate([SideType.PONDS], SideType.PONDS, coordinates=(0,-4)))
        session.place_candidate(session.prepare_candidate([SideType.HOUSE], SideType.GREEN, coordinates=(-3,-2)))
        session.place_candidate(session.prepare_candidate([SideType.STATION], SideType.STATION, coordinates=(-3,2)))

        session.watch_coordinates((0,8))
        session.watch_coordinates((0,-8))
        assert len(session.watched_open_coords) == 2

        # CSV
        file = "./tests/data/__test_save_load__.csv"
        session.save_to_csv(file)

        assert os.path.exists(file)

        loaded_csv_session = Session()
        assert len(loaded_csv_session.played_tiles) == 0    # assert session is empty before load
        loaded_csv_session.load_from_csv(file, simulate_tile_placement=False)

        assert_session_equal(session, loaded_csv_session)
        assert len(loaded_csv_session.watched_open_coords) == 0   # watched coordinates are not saved when saving to CSV

        os.remove(file)

        # DATABASE
        session_name = "test_session"
        session.save_to_database(session_name)

        sessions_df = session.get_all_sessions_from_database()
        assert sessions_df.shape[0] == 1  # expecting 1 row
        session_id = sessions_df.iloc[0]["id"]
        assert not pd.isna(session_id) and session_id

        loaded_database_session = Session(database)
        assert len(loaded_database_session.played_tiles) == 0  # assert session is empty before load
        loaded_database_session.load_from_database(session_id, simulate_tile_placement=False)

        assert_session_equal(session, loaded_database_session)
        assert_watched_coords_equal(session, loaded_database_session)

        session.delete_from_database(session_id)
        sessions_df = session.get_all_sessions_from_database()
        assert sessions_df.shape[0] == 0

    os.remove(database)

def test_load_no_watch():
    database = "./tests/data/__test_save_load__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with Session(database) as session:
        session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,0)))
        session.place_candidate(session.prepare_candidate([SideType.WOODS], SideType.WOODS, coordinates=(0,4)))

        session_name = "session_without_watch"
        session.save_to_database(session_name)

        sessions_df = session.get_all_sessions_from_database()
        assert sessions_df.shape[0] == 1  # expecting 1 row
        session_id = sessions_df.iloc[0]["id"]
        assert not pd.isna(session_id) and session_id

        loaded_database_session = Session(database)
        loaded_database_session.load_from_database(session_id, simulate_tile_placement=False)

        assert_session_equal(session, loaded_database_session)
        assert len(loaded_database_session.watched_open_coords) == 0

    os.remove(database)

def test_load_save_csv():
    session = Session()
    input_file = "./tests/data/group.csv"
    assert os.path.exists(input_file)

    session.load_from_csv(input_file, simulate_tile_placement=False)

    output_file = "./tests/data/group_temp.csv"
    session.save_to_csv(output_file)
    assert os.path.exists(output_file)

    assert filecmp.cmp(input_file, output_file, shallow=False)

    os.remove(output_file)

def test_save_same_name():
    database = "./tests/data/__test_save_load__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with Session(database) as session:
        input_file = "./tests/data/group.csv"
        assert os.path.exists(input_file)

        session.load_from_csv(input_file, simulate_tile_placement=False)

        session_name = "test_session"
        session.save_to_database(session_name)
        # save again with same name
        session.save_to_database(session_name)

        sessions_df = session.get_all_sessions_from_database()
        assert sessions_df.shape[0] == 2  # expecting 2 rows
        session_id_0 = sessions_df.iloc[0]["id"]
        session_id_1 = sessions_df.iloc[1]["id"]
        assert not pd.isna(session_id_0) and session_id_0
        assert not pd.isna(session_id_1) and session_id_1
        assert session_id_0 != session_id_1

    os.remove(database)

def test_autosave():
    database = "./tests/data/__test_autosave__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with Session(database) as session:

        session.autosave(None)
        session.autosave(None, undo_tile_placement=True)

        session.start()
        assert session.autosave_id == -1

        assert len(session.played_tiles) == 1
        session.autosave(list(session.played_tiles.values())[0])
        autosave_ids = session.database.find_session_ids_by_name(DatabaseConstants.AUTOSAVE_NAME)
        assert len(autosave_ids) == 1

        loaded_database_session = Session(database)
        loaded_database_session.load_from_database(autosave_ids[0], simulate_tile_placement=False)

        assert_session_equal(session, loaded_database_session)

        candidate = session.prepare_candidate([SideType.WOODS], SideType.WOODS, coordinates=(0,4))
        session.place_candidate(candidate)
        session.autosave(candidate)

        loaded_database_session.load_from_database(autosave_ids[0], simulate_tile_placement=False)
        assert_session_equal(session, loaded_database_session)

        undone_tile = session.undo_last_tile()
        session.autosave(undone_tile, undo_tile_placement=True)

        loaded_database_session.load_from_database(autosave_ids[0], simulate_tile_placement=False)
        assert_session_equal(session, loaded_database_session)

        # reset and start new session, ensure to reuse autosave
        session.start()
        assert len(session.played_tiles) == 1

        # assert that autosave is not overwritten by resetting
        loaded_database_session.load_from_database(autosave_ids[0], simulate_tile_placement=False)
        assert_session_not_equal(session, loaded_database_session)

        session.autosave(list(session.played_tiles.values())[0])

        autosave_ids = session.database.find_session_ids_by_name(DatabaseConstants.AUTOSAVE_NAME)
        assert len(autosave_ids) == 1

        loaded_database_session.load_from_database(autosave_ids[0], simulate_tile_placement=False)
        assert_session_equal(session, loaded_database_session)

    os.remove(database)

def test_save_load_simulation():
    session = Session()

    # place some tiles in a vertical line
    for i in range(30):
        session.place_candidate(session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(0,i*4)))

    file = "./tests/data/__test_save_load__.csv"
    session.save_to_csv(file)

    # no simulation expects exact same setup of tiles
    loaded_csv_session = Session()
    loaded_csv_session.load_from_csv(file, simulate_tile_placement=False)
    assert_session_equal(session, loaded_csv_session)

    # simulation expects a different setup,
    # as placing tiles only vertically will most likely be not the best
    loaded_csv_session_simulated = Session()
    loaded_csv_session_simulated.load_from_csv(file, simulate_tile_placement=True)

    assert_session_not_equal(session, loaded_csv_session_simulated)

    os.remove(file)

def test_compute_candidate_tiles_invalid_input():
    session = Session()
    valid_side_type_seq = compute_sequence([SideType.WOODS])
    invalid_side_type_seq = "some gargabe"
    valid_center_type = SideType.WOODS.to_character()
    invalid_center_type = "some gargabe"

    assert len(session.compute_candidate_tiles(side_type_seq=valid_side_type_seq, center_type=valid_center_type)) == 1
    assert len(session.compute_candidate_tiles(side_type_seq=invalid_side_type_seq, center_type=valid_center_type)) == 0
    assert len(session.compute_candidate_tiles(side_type_seq=valid_side_type_seq, center_type=invalid_center_type)) == 0
    assert len(session.compute_candidate_tiles(side_type_seq=invalid_side_type_seq, center_type=invalid_center_type)) == 0

def test_compute_candidate_tiles_first_tile():
    session = Session()

    for first_tile_type in SideType.get_values():
        side_type_seq = compute_sequence([first_tile_type for i in range(6)])
        center_type = first_tile_type.to_character()
        candidates = session.compute_candidate_tiles(side_type_seq=side_type_seq,
                                                    center_type=center_type)

        # if there are no tiles yet, the tile itself is the candidate
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.get_side_type_seq() == side_type_seq
        assert candidate.get_center().type.to_character() == center_type

        # no neighboring tiles yet, therefore all unknown
        for side in candidate.subsections.values():
            assert side.placement == Side.Placement.UNKNOWN_MATCH

def test_compute_candidate_tiles():
    session = Session()

    center_coordinate = (0,0)
    # place a center tile once for every type
    for first_tile_type in SideType.get_values():
        start_tile = session.prepare_candidate([first_tile_type], first_tile_type, coordinates=center_coordinate)
        session.place_candidate(start_tile)

        # compute candidates for all types and verify the placement evaluation
        for type in SideType.get_values():
            candidates = session.compute_candidate_tiles(side_type_seq=[type], center_type=type)

            if (type in TileEvaluation.RESTRICTED_DICT and first_tile_type not in TileEvaluation.RESTRICTED_DICT[type]) or\
               (first_tile_type in TileEvaluation.RESTRICTED_DICT and type not in TileEvaluation.RESTRICTED_DICT[first_tile_type]):
                assert len(candidates) == 0
            else:
                assert len(candidates) == 6

            for candidate in candidates:
                for side in candidate.get_sides().values():
                    assert side.type == type
                assert candidate.get_center().type == type

                contains_imperfect_sides = False
                for subsection, side in candidate.subsections.items():
                    if candidate.neighbor_coordinates[subsection.value] == center_coordinate:
                        # side connects to center

                        if type in TileEvaluation.RESTRICTED_DICT and \
                            first_tile_type in TileEvaluation.RESTRICTED_DICT[type]:
                                assert side.placement == Side.Placement.PERFECT_MATCH
                        elif first_tile_type in TileEvaluation.RESTRICTED_DICT and \
                            type in TileEvaluation.RESTRICTED_DICT[first_tile_type]:
                                assert side.placement == Side.Placement.PERFECT_MATCH
                        elif type in TileEvaluation.PERFECT_MATCH_DICT:
                            if first_tile_type in TileEvaluation.PERFECT_MATCH_DICT[type]:
                                assert side.placement == Side.Placement.PERFECT_MATCH
                            else:
                                assert side.placement == Side.Placement.IMPERFECT_MATCH
                                contains_imperfect_sides = True
                    else:
                        # no neighbor that side
                        assert side.placement == Side.Placement.UNKNOWN_MATCH

                if contains_imperfect_sides:
                    assert candidate.get_placement() == Tile.Placement.IMPERFECT
                else:
                    assert candidate.get_placement() == Tile.Placement.PERFECT

        session.undo_last_tile()

def test_compute_tile_ratings():
    session = Session()

    center_coordinate = (0,0)
    # place a center tile once for every type
    for first_tile_type in SideType.get_values():
        start_tile = session.prepare_candidate([first_tile_type], first_tile_type, coordinates=center_coordinate)
        session.place_candidate(start_tile)

        # compute candidates for all types and verify the placement evaluation
        for type in SideType.get_values():
            side_type_seq = compute_sequence([type for i in range(6)])
            center_type = type.to_character()
            candidates = session.compute_candidate_tiles(side_type_seq=side_type_seq,
                                                        center_type=center_type)

            rated_candidates = session.compute_tile_ratings(candidates)
            count_placement_not_possible = sum(1 for tile in candidates if tile.get_placement() == Tile.Placement.NOT_POSSIBLE)
            assert len(rated_candidates) == len(candidates) - count_placement_not_possible

        session.undo_last_tile()

def test_get_rotated_candidate():
    session = Session()
    session.load_from_csv("./tests/data/rotation_party_disallowed.csv", simulate_tile_placement=False)

    # same sided hexagon
    candidates = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    assert len(candidates) > 0
    assert session.get_rotated_candidate(candidates[0], 1) == None

    # only one orientation allowed, therefore no rotation
    candidates = session.compute_candidate_tiles([SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.RIVER], SideType.RIVER)
    eval_candidates = [candidate for candidate in candidates if candidate.coordinates == (3, 2)]
    assert len(eval_candidates) == 1
    assert session.get_rotated_candidate(eval_candidates[0], 1) == None

    # mirrored rotation
    original_side_types =\
        [SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN]
    expected_rotated_side_types =\
        [SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN]
    candidate = session.prepare_candidate(original_side_types, SideType.TRAIN, (3, -2))
    for i in [-1, 1]:
        rotated_candidate = session.get_rotated_candidate(candidate, i)
        assert [side.type for side in rotated_candidate.get_sides().values()] == expected_rotated_side_types

        for j in [-1, 1]:
            again_rotated_candidate = session.get_rotated_candidate(rotated_candidate, j)
            assert [side.type for side in again_rotated_candidate.get_sides().values()] == original_side_types

    # restricted rotation
    expected_rotated_sequences = [
        [SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS],
        [SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS],
        [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.PONDS, SideType.PONDS],
        [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN]
    ]

    candidates = session.compute_candidate_tiles([SideType.PONDS, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS], SideType.PONDS)
    eval_candidates = [candidate for candidate in candidates if candidate.coordinates == (3, 2)]
    assert len(eval_candidates) == 4
    for candidate in eval_candidates:
        assert [side.type for side in candidate.get_sides().values()] in expected_rotated_sequences

    curr_candidate = eval_candidates[0]
    for i in range(len(expected_rotated_sequences)):
        rotated_candidate = session.get_rotated_candidate(curr_candidate, 1)
        assert rotated_candidate != curr_candidate
        assert [side.type for side in rotated_candidate.get_sides().values()] in expected_rotated_sequences

        rotated_candidate = session.get_rotated_candidate(rotated_candidate, -1)
        assert rotated_candidate == curr_candidate

        rotated_candidate = session.get_rotated_candidate(curr_candidate, 1)
        assert rotated_candidate != curr_candidate

        # invalid rotation value
        for rot in range(-10, 11):
            if rot not in [-1, 1]:
                assert session.get_rotated_candidate(candidates[0], rot) is None
            else:
                assert session.get_rotated_candidate(candidates[0], rot) is not None

        curr_candidate = rotated_candidate

def test_get_placement_counts():
    session = Session()
    assert session.get_perfect_placement_percentage() == 0

    session.load_from_csv("./tests/data/perfectly_closed_neighbor.csv", simulate_tile_placement=False)

    session.place_candidate(
        session.prepare_candidate([SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN],
                                          SideType.GREEN, (3,2))
    )

    assert session.get_open_count() == 11
    assert session.get_closed_count() == 3
    assert session.get_perfect_placement_count() == 2
    assert session.get_imperfect_placement_count() == 1
    assert session.get_open_placement_count(Tile.Placement.PERFECT) == 9
    assert session.get_open_placement_count(Tile.Placement.IMPERFECT) == 2
    assert session.get_perfect_placement_percentage() == 66.67

def test_compute_open_tiles():
    session = Session()

    assert len(session.open_coords) == 1
    assert next(iter(session.open_coords)) == (0,0)

    candidates = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    assert len(candidates) == 1
    session.place_candidate(candidates[0])

    assert len(session.open_coords) == 6

    # assert that open tiles are returned clockwised, starting from TOP
    for i, subsection in enumerate(TileSubsection.get_side_values()):
        assert Tile.get_coordinates((0,0), subsection) == list(session.open_coords.keys())[i]

    session.load_from_csv("./tests/data/surrounding_tiles.csv", simulate_tile_placement=False)
    assert len(session.open_coords) == 25

    # assert that neighbors of tiles that have been played earlier are appearing first in the list
    session.load_from_csv("./tests/data/open_tiles_suggestion_order.csv", simulate_tile_placement=False)
    assert len(session.open_coords) >= 3
    assert list(session.open_coords.keys())[0] == (3,2)   # UPPER_RIGHT
    assert list(session.open_coords.keys())[1] == (0,-4)  # BOTTOM
    assert list(session.open_coords.keys())[2] == (-3,2)  # UPPER_LEFT

def test_compute_open_tiles_for_tile():
    session = Session()

    assert session.open_coords is not None
    assert len(session.open_coords) == 1
    assert next(iter(session.open_coords)) == (0,0)

    assert session.compute_open_coords_for_tile(None) == {}
    some_tile = Tile(SideType.GREEN, SideType.GREEN, (0,4))
    assert session.compute_open_coords_for_tile(some_tile) == {}

    candidates = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    session.place_candidate(candidates[0])

    candidates = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    assert len(candidates) > 0

    candidate = candidates[0]
    open_tiles_for_candidate = session.compute_open_coords_for_tile(candidate)

    assert open_tiles_for_candidate != session.open_coords
    assert candidate.coordinates in session.open_coords
    assert candidate.coordinates not in open_tiles_for_candidate

    for subsection in TileSubsection.get_side_values():
        if candidate.neighbor_coordinates[subsection.value] not in session.played_tiles:
            assert candidate.neighbor_coordinates[subsection.value] in open_tiles_for_candidate


def test_watch_unwatch_coordinates_tiles_seen():
    session_unmodified = Session()
    session_unmodified.load_from_csv("./tests/data/num_seen_tiles.csv", simulate_tile_placement=False)

    session = Session()
    session.load_from_csv("./tests/data/num_seen_tiles.csv", simulate_tile_placement=False)

    def get_tile_placement(played_tiles, tile):
        for subsection, side in tile.get_sides().items():
            neighbor_coordinates = tile.neighbor_coordinates[subsection.value]
            if neighbor_coordinates in played_tiles:
                opposing_side = played_tiles[neighbor_coordinates].get_sides()[Tile.get_opposing(subsection)]
                side.placement = TileEvaluation.compute_side_placement_match(side.type, opposing_side.type)

        return tile.get_placement()

    def compute_num(played_tiles, open_coords):
        # computes the number of tiles that have already been played that would
        # match all known sides of the open position
        count = 0
        for tile in played_tiles.values():
            side_types = [side.type for side in tile.get_sides().values()]
            for i in range(len(side_types)):
                rotated_sides = side_types[i:] + side_types[:i]
                candidate = Tile(side_types=rotated_sides,
                                 center_type=tile.get_center().type,
                                 coordinates=open_coords)

                placement = get_tile_placement(played_tiles, candidate)
                if placement == Tile.Placement.PERFECT or placement == Tile.Placement.PERFECTLY_CLOSED:
                    count += 1
                    break
        return count

    initial_expectation = {
        (3,2) : 0,
        (6,4) : 3,
        (6,8) : 4,
        (3,10) : 3,
        (0,12) : 5,
        (-3,10) : 1,
        (-6,8) : 9,
        (-6,4) : 0,
        (-6,0) : 3,
        (-6,-4) : 5,
        (-3,-6) : 2,
        (0,-8) : 2,
        (3,-10) : 0,
        (3,-14) : 15,
        (6,-16) : 5,
        (9,-18) : 15,
        (12,-16) : 9,
        (12,-12) : 5,
        (9,-10) : 1,
        (9,-6) : 3,
        (9,-2) : 0,
        (12,0) : 5,
        (12,4) : 13,
        (12,8) : 15,
        (9,10) : 15
    }

    after_place_expectation = {
        (3,2) : 0,
        (6,8) : 1,
        (3,10) : 3,
        (0,12) : 5,
        (-3,10) : 1,
        (-6,8) : 10,
        (-6,4) : 1,
        (-6,0) : 3,
        (-6,-4) : 5,
        (-3,-6) : 2,
        (0,-8) : 3,
        (3,-10) : 0,
        (3,-14) : 16,
        (6,-16) : 5,
        (9,-18) : 16,
        (12,-16) : 10,
        (12,-12) : 6,
        (9,-10) : 1,
        (9,-6) : 4,
        (9,-2) : 0,
        (12,0) : 6,
        (12,4) : 14,
        (12,8) : 16,
        (9,10) : 16
    }

    def assert_num_seen(expectation):
        assert len(session.watched_open_coords) == len(expectation)
        for coords, expected_num in expectation.items():
            assert expected_num == compute_num(session.played_tiles, coords)
            assert expected_num == session.get_num_played_tiles_matching_perfectly(coords)
            assert expected_num == session.watched_open_coords[coords]

    placement_coordinates = (6,4)
    def prepare_candidate():
        return session.prepare_candidate(
            [SideType.GREEN, SideType.TRAIN, SideType.TRAIN, SideType.WOODS, SideType.CROPS, SideType.GREEN],
            SideType.GREEN, placement_coordinates
            )

    assert len(session.watched_open_coords) == 0
    assert session.coordinate_watch_candidate == None
    assert session.unwatch_coordinates(placement_coordinates) == False  # not yet watched

    for coords in initial_expectation.keys():
        session.select_coordinates(coords)
        assert session.coordinate_watch_candidate == (coords, initial_expectation[coords])

        session.watch_coordinates(coords)

        session.select_coordinates(coords)
        assert session.coordinate_watch_candidate == None

    assert placement_coordinates in session.watched_open_coords

    assert_num_seen(initial_expectation)
    assert session.seen_tile_sides_tree == session_unmodified.seen_tile_sides_tree

    session.place_candidate(prepare_candidate())
    assert_num_seen(after_place_expectation)

    assert session.watch_coordinates(placement_coordinates) == False  # not open anymore
    assert placement_coordinates not in session.watched_open_coords

    session.undo_last_tile()
    assert_num_seen(initial_expectation)
    assert session.seen_tile_sides_tree == session_unmodified.seen_tile_sides_tree

    assert placement_coordinates in session.watched_open_coords

    session.place_candidate(prepare_candidate())
    assert_num_seen(after_place_expectation)

    assert placement_coordinates not in session.watched_open_coords

    for coords in after_place_expectation.keys():
        session.unwatch_coordinates(coords)

    assert len(session.watched_open_coords) == 0