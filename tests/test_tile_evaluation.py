from contextlib import contextmanager

from src.side import Side
from src.side_type import SideType
from src.tile import Tile
from src.tile_subsection import TileSubsection
from src.session import Session
from src.tile_evaluation import TileEvaluation
from src.tile_evaluation_factory import TileEvaluationFactory

from tests.utils import get_sequence

@contextmanager
def temporary_assignments(obj, **kwargs):
    original_values = {attr: getattr(obj, attr) for attr in kwargs}
    for attr, new_value in kwargs.items():
        setattr(obj, attr, new_value)
    try:
        yield
    finally:
        for attr, original_value in original_values.items():
            setattr(obj, attr, original_value)

def assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, rating_attribute):
    def get_rating_value(rated_tile):
        if rating_attribute == 'rating':
            return rated_tile.rating
        else:
            return getattr(rated_tile.rating_detail, rating_attribute)

    high_rating_dict = {}

    for coordinates, side_types_rating_group_e in expected_candidate_coordinate_rating_groups.items():
        # assert rating order within the coordinates rotations itself
        rating_list = {}
        eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == coordinates]

        sorted_candidates = sorted(eval_candidates, key=get_rating_value, reverse=True)

        # collect highest rating per group
        if sorted_candidates:
            high_rating_dict[coordinates] = get_rating_value(sorted_candidates[0])

        for candidate in sorted_candidates:
            actual_subsection_side_types = candidate.tile.get_side_type_seq()

            rating_value = get_rating_value(candidate)
            if rating_value in rating_list:
                rating_list[rating_value].append(actual_subsection_side_types)
            else:
                rating_list[rating_value] = [actual_subsection_side_types]

        expected_side_type_seq_rating_groups = []
        for side_types_list in side_types_rating_group_e:
            side_type_seq_rating_group = []
            for side_types in side_types_list:
                if isinstance(side_types, str):
                    side_type_seq_rating_group.append(side_types)
                else:
                    side_type_seq_rating_group.append(get_sequence(side_types))
            expected_side_type_seq_rating_groups.append(side_type_seq_rating_group)

        assert [sorted(group) for group in expected_side_type_seq_rating_groups] == \
            [sorted(side_type_list) for side_type_list in rating_list.values()]

        ratings = list(rating_list.keys())
        for i in range(len(ratings)):
            if i > 0:
                assert ratings[i] < ratings[i-1]

    # assert that the highest rating for each group is properly ordered
    high_ratings = [rating for rating in high_rating_dict.values()]
    for i in range(len(high_ratings)):
        if i > 0:
            assert high_ratings[i] < high_ratings[i-1]

def assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session):
    tile_evaluation = TileEvaluationFactory.create(candidate_tiles, session)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    for coordinates in expected_candidate_coordinate_perspective_groups.keys():
        eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == coordinates]
        assert len(eval_candidates) == len(expected_candidate_coordinate_perspective_groups[coordinates])

        for candidate in eval_candidates:
            actual_subsection_side_types = [side.type for side in candidate.tile.get_sides().values()]

            expectation = None
            for side_types, expected_group_type_distant_group_extensions in expected_candidate_coordinate_perspective_groups[coordinates]:
                if actual_subsection_side_types == side_types:
                    expectation = []
                    for group_type, distant_group_extension in expected_group_type_distant_group_extensions:
                        expectation.append([
                                group_type,
                                sorted(distant_group_extension)
                            ])

            assert expectation is not None

            perspective_groups = tile_evaluation.get_distant_groups_for_tile(candidate.tile, candidate.rating_detail.open_coords)

            group_extension_distances = []
            for group_id, distant_groups in perspective_groups.items():
                group_extension_distances.append([
                        candidate.tile.group_participation[group_id].group.type,
                        sorted([(session.groups[distant_group_id].type, distance)
                                for distant_group_id, (distance, extension_type, num_sides) in distant_groups.items()])
                    ])

            assert sorted(expectation) == sorted(group_extension_distances)

def test_session_begin():
    session = Session()
    candidate_tiles = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert len(rated_candidates) == 1
    assert rated_candidates[0].rating > 0

def test_compute_side_placement_match():
    for type in SideType.all_types():
        for opp_type in SideType.all_types():
            placement = TileEvaluation.compute_side_placement_match(type, opp_type)

            if type is SideType.UNKNOWN or opp_type is SideType.UNKNOWN:
                assert placement == Side.Placement.UNKNOWN_MATCH

            elif (opp_type in TileEvaluation.RESTRICTED_DICT and type not in TileEvaluation.RESTRICTED_DICT[opp_type]) or\
               (type in TileEvaluation.RESTRICTED_DICT and opp_type not in TileEvaluation.RESTRICTED_DICT[type]):
                assert placement == Side.Placement.NOT_POSSIBLE

            elif opp_type in TileEvaluation.RESTRICTED_DICT and \
                type in TileEvaluation.RESTRICTED_DICT[opp_type]:
                    assert placement == Side.Placement.PERFECT_MATCH

            elif type in TileEvaluation.RESTRICTED_DICT and \
                opp_type in TileEvaluation.RESTRICTED_DICT[type]:
                    assert placement == Side.Placement.PERFECT_MATCH

            elif opp_type in TileEvaluation.PERFECT_MATCH_DICT:
                if type in TileEvaluation.PERFECT_MATCH_DICT[opp_type]:
                    assert placement == Side.Placement.PERFECT_MATCH
                else:
                    assert placement == Side.Placement.IMPERFECT_MATCH

def test_side_placement_rating():
    session = Session()

    center_coordinate = (0,0)
    # place a center tile once for every type
    for first_tile_type in SideType.get_values():
        start_tile = session.prepare_candidate([first_tile_type], first_tile_type, coordinates=center_coordinate)
        session.place_candidate(start_tile)

        # compute candidates for all types and verify the placement evaluation
        for type in SideType.get_values():
            rated_tiles = session.compute_tile_ratings(session.compute_candidate_tiles([type], type))

            placement = TileEvaluation.compute_side_placement_match(type, first_tile_type)
            if placement == Side.Placement.NOT_POSSIBLE:
                assert not rated_tiles
                continue

            for rated_tile in rated_tiles:
                side_rating = TileEvaluation._BASE_RATING[placement][Tile.Placement.PERFECT]

                # since we connect at just one side, we expect all other sides to be an unknown match
                assert rated_tile.rating_detail.tile_placement_rating == \
                    side_rating + 5 * TileEvaluation._BASE_RATING[Side.Placement.UNKNOWN_MATCH][Tile.Placement.UNKNOWN]

        session.undo_last_tile()

def test_side_placement_imperfect():
    session = Session()
    session.load_from_csv("./tests/data/perfectly_closed_neighbor.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (3,2) : [
            [
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles([SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'tile_placement_rating')

def test_side_placement_plug_hole():
    session = Session()
    session.load_from_csv("./tests/data/group_ponds_station.csv", simulate_tile_placement=False)

    candidate_tile = session.prepare_candidate([SideType.GREEN], SideType.GREEN, coordinates=(3,2))

    for rated_tile in session.compute_tile_ratings([candidate_tile]):
        assert rated_tile.rating_detail.tile_placement_rating == \
                        5 * TileEvaluation._BASE_RATING[Side.Placement.PERFECT_MATCH][Tile.Placement.PERFECT] +\
                        1 * TileEvaluation._BASE_RATING[Side.Placement.PERFECT_MATCH][Tile.Placement.PERFECTLY_CLOSED] +\
                        TileEvaluation._PLUG_HOLE_VALUE

def test_side_placement_perfectly_closed_neighbor():
    session = Session()
    session.load_from_csv("./tests/data/perfectly_closed_neighbor.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == (3,2)]
    assert len(eval_candidates) == 6

    expected_subsection_side_types_order = [
        # num perfectly closed, num perfect->perfect, num perfect->imperfect,
        # num imperfect->perfect, num imperfect->imperfect, num unknown,
        # expected side types
        (2, 1, 2,
         0, 0, 1,
         {
            TileSubsection.TOP : SideType.GREEN,
            TileSubsection.UPPER_RIGHT : SideType.WOODS,
            TileSubsection.LOWER_RIGHT : SideType.WOODS,
            TileSubsection.BOTTOM : SideType.GREEN,
            TileSubsection.LOWER_LEFT : SideType.GREEN,
            TileSubsection.UPPER_LEFT : SideType.GREEN
        }),
        (2, 1, 1,
         0, 1, 1,
         {
            TileSubsection.TOP : SideType.GREEN,
            TileSubsection.UPPER_RIGHT : SideType.GREEN,
            TileSubsection.LOWER_RIGHT : SideType.WOODS,
            TileSubsection.BOTTOM : SideType.WOODS,
            TileSubsection.LOWER_LEFT : SideType.GREEN,
            TileSubsection.UPPER_LEFT : SideType.GREEN
        }),
        (2, 0, 1,
         1, 1, 1,
         {
            TileSubsection.TOP : SideType.WOODS,
            TileSubsection.UPPER_RIGHT : SideType.WOODS,
            TileSubsection.LOWER_RIGHT : SideType.GREEN,
            TileSubsection.BOTTOM : SideType.GREEN,
            TileSubsection.LOWER_LEFT : SideType.GREEN,
            TileSubsection.UPPER_LEFT : SideType.GREEN
        }),
        (1, 1, 0,
         1, 2, 1,
         {
            TileSubsection.TOP : SideType.GREEN,
            TileSubsection.UPPER_RIGHT : SideType.GREEN,
            TileSubsection.LOWER_RIGHT : SideType.GREEN,
            TileSubsection.BOTTOM : SideType.WOODS,
            TileSubsection.LOWER_LEFT : SideType.WOODS,
            TileSubsection.UPPER_LEFT : SideType.GREEN
        }),
        (1, 0, 1,
         2, 1, 1,
         {
            TileSubsection.TOP : SideType.WOODS,
            TileSubsection.UPPER_RIGHT : SideType.GREEN,
            TileSubsection.LOWER_RIGHT : SideType.GREEN,
            TileSubsection.BOTTOM : SideType.GREEN,
            TileSubsection.LOWER_LEFT : SideType.GREEN,
            TileSubsection.UPPER_LEFT : SideType.WOODS
        }),
        (0, 1, 1,
         2, 1, 1,
         {
            TileSubsection.TOP : SideType.GREEN,
            TileSubsection.UPPER_RIGHT : SideType.GREEN,
            TileSubsection.LOWER_RIGHT : SideType.GREEN,
            TileSubsection.BOTTOM : SideType.GREEN,
            TileSubsection.LOWER_LEFT : SideType.WOODS,
            TileSubsection.UPPER_LEFT : SideType.WOODS
        })
    ]

    for i in range(len(eval_candidates)):
        actual_subsection_side_types = \
            { sub : side.type for sub, side in eval_candidates[i].tile.get_sides().items()}

        num_perfectly_closed, num_perfect_to_perfect, num_perfect_to_imperfect,\
            num_imperfect_to_perfect, num_imperfect_to_imperfect, num_unknown, \
            expected_subsection_side_types = \
                expected_subsection_side_types_order[i]

        assert actual_subsection_side_types == expected_subsection_side_types
        assert eval_candidates[i].rating_detail.tile_placement_rating == \
            num_perfectly_closed * TileEvaluation._BASE_RATING[Side.Placement.PERFECT_MATCH][Tile.Placement.PERFECTLY_CLOSED] +\
            num_perfect_to_perfect * TileEvaluation._BASE_RATING[Side.Placement.PERFECT_MATCH][Tile.Placement.PERFECT] +\
            num_perfect_to_imperfect * TileEvaluation._BASE_RATING[Side.Placement.PERFECT_MATCH][Tile.Placement.IMPERFECT] +\
            num_imperfect_to_perfect * TileEvaluation._BASE_RATING[Side.Placement.IMPERFECT_MATCH][Tile.Placement.PERFECT] +\
            num_imperfect_to_imperfect * TileEvaluation._BASE_RATING[Side.Placement.IMPERFECT_MATCH][Tile.Placement.IMPERFECT] +\
            num_unknown * TileEvaluation._BASE_RATING[Side.Placement.UNKNOWN_MATCH][Tile.Placement.UNKNOWN]

        if i > 0:
            if eval_candidates[i].rating_detail.tile_placement_rating < \
               eval_candidates[i-1].rating_detail.tile_placement_rating:
                assert eval_candidates[i].rating < eval_candidates[i-1].rating
            else:
                assert eval_candidates[i].rating <= eval_candidates[i-1].rating

def test_num_perfectly_closed():
    session = Session()
    session.load_from_csv("./tests/data/perfectly_closed_neighbor.csv", simulate_tile_placement=False)

    session.place_candidate(
        session.prepare_candidate(
            [SideType.TRAIN, SideType.GREEN, SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.GREEN],
            SideType.TRAIN,
            (6,4)
            )
        )

    candidate = session.prepare_candidate(
            [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN],
            SideType.WOODS,
            (3,2)
            )

    assert candidate.get_num_perfectly_closed(session.played_tiles) == 3

    candidate = session.prepare_candidate(
            [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN],
            SideType.WOODS,
            (3,2)
            )

    assert candidate.get_num_perfectly_closed(session.played_tiles) == 2

def test_neighbor_compatibility_score_dictionaries():
    for neighbor_scores in [TileEvaluation._DIRECT_NEIGHBOR_COMPATIBILITY_SCORE,
                            TileEvaluation._OTHER_NEIGHBOR_COMPATIBILITY_SCORE]:
        combination_list = {}
        for score, side_type_dict in neighbor_scores:
            for type in SideType.get_values():
                for other_type in SideType.get_values():
                    if type in side_type_dict:
                        if other_type in side_type_dict[type]:
                            combination = (type, other_type)
                            opposite_combination = (other_type, type)
                            if combination in combination_list or opposite_combination in combination_list:
                                print(combination)
                                assert False  # every combination should be unique
                            combination_list[combination] = 1

def test_no_neighbor_compatibility():
    session = Session()
    session.load_from_csv("./tests/data/tile_evaluation_neighbor_compatibility.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (0,-4) : [
            [
                [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS],
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN],
                [SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS],
                [SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS],
                [SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS]
            ]
        ],
        (0,8) : [
            [
                # no compatibility at all
                [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS],
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN],
                [SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS],
                [SideType.WOODS, SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN],
                [SideType.WOODS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS],
                [SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.CROPS],
        SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'neighbor_compatibility_rating')

def test_type_demotion_rating_side_consideration():
    session = Session()
    session.load_from_csv("./tests/data/neighbor_compatibility_unrestricted_restricted.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (6,-4) : [
            [
                [SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.RIVER],
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.RIVER],
            ],
            [
                [SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.RIVER, SideType.GREEN]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.RIVER],
        SideType.RIVER)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'neighbor_type_demotion_rating')

def test_neighbor_compatibility_with_no_open_neighbors():
    session = Session()
    session.load_from_csv("./tests/data/neighbor_compatibility_no_open_neighbors.csv", simulate_tile_placement=False)

    # all non-restricted tile
    candidate_tiles = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == (3,2)]
    assert len(eval_candidates) == 1

    assert eval_candidates[0].rating_detail.neighbor_compatibility_rating == 0

    # tile with restrictions
    candidate_tiles = session.compute_candidate_tiles([SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.WOODS], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == (9,-2)]
    assert len(eval_candidates) == 1

    assert eval_candidates[0].rating_detail.neighbor_compatibility_rating == 0

def test_restricted_orientation():
    session = Session()
    session.load_from_csv("./tests/data/restricted_orientation_num_played_tiles.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN],
        SideType.RIVER)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    eval_candidates = [rc for rc in rated_candidates if rc.tile.coordinates == (-12,-8)]
    assert len(eval_candidates) == 2

    expected_high_rating_subsection_side_types = [
        {
        TileSubsection.TOP : SideType.GREEN,
        TileSubsection.UPPER_RIGHT : SideType.RIVER,
        TileSubsection.LOWER_RIGHT : SideType.GREEN,
        TileSubsection.BOTTOM : SideType.GREEN,
        TileSubsection.LOWER_LEFT : SideType.GREEN,
        TileSubsection.UPPER_LEFT : SideType.RIVER
        }
    ]

    actual_subsection_side_types = { sub : side.type for sub, side in eval_candidates[0].tile.get_sides().items()}
    assert actual_subsection_side_types in expected_high_rating_subsection_side_types
    assert eval_candidates[0].rating_detail.restricted_type_orientation_rating > \
            eval_candidates[1].rating_detail.restricted_type_orientation_rating

def test_neighbor_type_demotion():
    session = Session()
    session.load_from_csv("./tests/data/too_many_types_demotion.csv", simulate_tile_placement=False)

    # the open tiles at (6,4) and (6,8) already have 4 different types, which is considered the maximum

    # types that are not compatible and should therefore receive a demotion for too many types
    expected_too_many_type_demotion_types = [SideType.HOUSE, SideType.RIVER]

    # restricted types that would force the placement of a station for a perfectly closed tile,
    # but station-incompatible types present
    expected_station_required_but_imperfect_types = [SideType.RIVER]

    expected_non_restricted_facing_restricted = [SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.CROPS, SideType.PONDS]

    # place a candidate at (9,6) that connects to both of the above mentioned tiles
    for type in SideType.get_values():
        # use type for both sides that are each connecting to one of the above mentioned open tiles
        for ul_type in [SideType.GREEN, type]:
            for ll_type in [SideType.GREEN, type]:
                eval_candidates = session.compute_tile_ratings(
                    [session.prepare_candidate([SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, ll_type, ul_type],
                                                SideType.GREEN, (9,6))]
                    )
                assert len(eval_candidates) == 1
                candidate = eval_candidates[0]

                expected_multiplier = 0
                if type in expected_too_many_type_demotion_types:
                    expected_multiplier += sum([1 if t == type else 0 for t in [ul_type, ll_type]])
                if ul_type in expected_station_required_but_imperfect_types:
                    expected_multiplier += 1
                elif ul_type in expected_non_restricted_facing_restricted:
                    expected_multiplier += 4/5  # 4 out of 5 sides are known
                if ll_type in expected_station_required_but_imperfect_types:
                    expected_multiplier += 1
                elif ll_type in expected_non_restricted_facing_restricted:
                    expected_multiplier += 4/5  # 4 out of 5 sides are known

                assert candidate.rating_detail.neighbor_type_demotion_rating == \
                        round(expected_multiplier * TileEvaluation._TYPE_DEMOTION_RATING_VALUE)

def test_station_type_check_restricted():
    session = Session()
    session.load_from_csv("./tests/data/station_demotion_river_train.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (3,-2) : [
            [
                # no demotion, as train builds towards perfectly station compatible open tile
                [SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN]
            ],
            [
                # 2x demotion because green side top faces river above and train side lower left faces green on the left
                [SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN]
            ]
        ],
        (-3,10) : [
            [
                # 1x demotion for station imcompatibility of open tile and 1x demotion for facing restricted
                [SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN],
                [SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.TRAIN, SideType.GREEN, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.GREEN],
        SideType.TRAIN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, "neighbor_type_demotion_rating")

def test_group_size_rating_restricted_boost():
    session = Session()
    session.load_from_csv("./tests/data/group_size_extension.csv", simulate_tile_placement=False)

    # we solely want to check for the group size here and do not want to consider the group size itself
    with temporary_assignments(TileEvaluation,
                              _PERSPECTIVE_GROUPS_MAX_DISTANCE_NON_RESTRICTED_TYPES=-1,
                              _PERSPECTIVE_GROUPS_MAX_DISTANCE_RESTRICTED_TYPES=-1):
        expected_candidate_coordinate_rating_groups = {
            # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
            # train group extension
            (-3,-6) : [
                [
                    [SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS],
                    [SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE]
                ]
            ],
            # woods group extension
            (3,10) : [
                [
                    [SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN]
                ],
                [
                    [SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN]
                ]
            ],
            # house group extension
            (6,0) : [
                [
                    [SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE]
                ],
                [
                    [SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN],
                    [SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS],
                    [SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS]
                ]
            ],
            # no group extension (only new groups)
            (-6,8) : [
                [
                    [SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS],
                    [SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE],
                    [SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN]
                ],
                [  # house group is directly closed, therefore worse rating than the others
                    [SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN, SideType.WOODS, SideType.WOODS]
                ]
            ]
        }

        candidate_tiles = session.compute_candidate_tiles([SideType.WOODS, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.HOUSE, SideType.TRAIN], SideType.TRAIN)
        rated_candidates = session.compute_tile_ratings(candidate_tiles)

        assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, "group_rating")

def test_group_size_rating():
    session = Session()
    session.load_from_csv("./tests/data/group_size_extension.csv", simulate_tile_placement=False)

    # we solely want to check for the group size here and do not want to consider the group size itself
    with temporary_assignments(TileEvaluation,
                              _PERSPECTIVE_GROUPS_MAX_DISTANCE_NON_RESTRICTED_TYPES=-1,
                              _PERSPECTIVE_GROUPS_MAX_DISTANCE_RESTRICTED_TYPES=-1):
        expected_candidate_coordinate_rating_groups = {
            # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
            (0,12) : [
                [
                    [SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.GREEN],
                    [SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.WOODS],
                    [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS]
                ],
                [
                    [SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS],
                ],
                [
                    [SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN],
                    [SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.WOODS]
                ]
            ]
        }

        candidate_tiles = session.compute_candidate_tiles([SideType.WOODS, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN], SideType.GREEN)
        rated_candidates = session.compute_tile_ratings(candidate_tiles)
        assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_group_size_rating_ponds_station():
    session = Session()
    session.load_from_csv("./tests/data/group_river_ponds_train_station.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (3,2) : [
            [
                [SideType.GREEN, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS],
                [SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS]
            ],
            [
                [SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS, SideType.PONDS],
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS]
            ],
            [
                [SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN],
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN]
            ]
        ],
        (6,-4) : [
            [
                [SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS, SideType.PONDS],
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN, SideType.PONDS]
            ],
            [
                [SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN],
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles([SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.GREEN], SideType.PONDS)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_group_size_rating_isolated():
    session = Session()
    session.load_from_csv("./tests/data/group_isolated_side.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (0,-4) : [
            [
                get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 1),
                get_sequence([SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN], 2),
                get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 3)
            ],
            [
                get_sequence([SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN], 0)
            ],
            [
                get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 5),
                get_sequence([SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN], 4)
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        get_sequence([SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS, SideType.GREEN, SideType.WOODS], 3),
        SideType.WOODS
        )
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_get_surrounding_tiles():
    session = Session()
    session.load_from_csv("./tests/data/surrounding_tiles.csv", simulate_tile_placement=False)

    expected_surrounding_tiles_for_coordinate = {
        # coordinates, (num_rings=1, num_rings=2, num_rings=3)
        (0,0) : (6,11,14),
        (0,4) : (7,11,13),
        (3,14) : (2,4,8),
        (9,-6) : (2,3,7)
    }

    tile_evaluation = TileEvaluationFactory.create(None, session)
    for coords, expected_num_surrounding_tiles_for_num_rings in expected_surrounding_tiles_for_coordinate.items():
        print(expected_num_surrounding_tiles_for_num_rings)
        for i in range(len(expected_num_surrounding_tiles_for_num_rings)):
            actual_surrounding_tiles = tile_evaluation.get_surrounding_tiles(center_coord=coords, num_rings=i+1)
            assert expected_num_surrounding_tiles_for_num_rings[i] == len(actual_surrounding_tiles)

def test_neighbor_group_consideration():
    session = Session()
    session.load_from_csv("./tests/data/surrounding_tiles.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (6,8) : [
            [
                [SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS]
            ],
            [
                [SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS]
            ],
            [
                [SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS]
            ],
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS]
            ],
            [
                [SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE]
            ],
            [
                [SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE],
        SideType.CROPS)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_neighbor_group_interference():
    session = Session()
    session.load_from_csv("./tests/data/surrounding_tiles.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (6,8) : [
            [
                [SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS]
            ],
            [
                [SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS]
            ],
            [
                [SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE, SideType.CROPS],
                [SideType.HOUSE, SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS]
            ],
            [
                [SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE],
                [SideType.HOUSE, SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.CROPS, SideType.CROPS, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.HOUSE],
        SideType.CROPS)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'neighbor_group_interference_rating')

def test_session_open_tiles_ordering():
    session = Session()
    session.load_from_csv("./tests/data/open_tiles_suggestion_order.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.GREEN], SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    # assert that the ordering of open tiles received by the session:
    # * prefers tiles that have been played earlier
    # * prefers the neighbors of a tile in clockwise orientation, starting from TOP
    assert len(rated_candidates) >= 3
    assert rated_candidates[0].tile.coordinates == (3,2)   # neighbor of (0,0) -> UPPER_RIGHT
    assert rated_candidates[1].tile.coordinates == (-3,2)  # neighbor of (0,0) -> UPPER_LEFT
    assert rated_candidates[2].tile.coordinates == (9,2)  # neighbor of another tile, played later


def test_get_distant_groups():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_extensions.csv", simulate_tile_placement=False)

    tile_evaluation = TileEvaluationFactory.create(None, session)

    expectation = {
        # coordinates: {allowed_number_of_hops: list of tuples with distance and group type}
        (0,-20) : {  # valid coordinate
            -1: [],
            0: [
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(1, ((0,-20), (3,-22),))], SideType.CROPS)
            ],
            1 : [
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(1, ((0,-20), (3,-22),)),
                  (2, ((0,-20), (3,-22), (6,-20),))], SideType.CROPS),
                ([(2, ((0,-20), (3,-22), (6,-20),))], SideType.WOODS),
                ([(2, ((0,-20), (-3,-18), (-3,-14),))], SideType.WOODS)
            ],
            2 : [
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(1, ((0,-20), (3,-22),)),
                  (2, ((0,-20), (3,-22), (6,-20),))], SideType.CROPS),
                ([(2, ((0,-20), (3,-22), (6,-20),)),
                  (3, ((0,-20), (3,-22), (6,-20), (9,-22),))], SideType.WOODS),
                ([(2, ((0,-20), (-3,-18), (-3,-14),))], SideType.WOODS),
                ([(3, ((0,-20), (-3,-18), (-3,-14), (-3,-10),))], SideType.CROPS)
            ],
            3 : [
                ([(0, ((0,-20),))], SideType.RIVER),
                ([(0, ((0,-20),)),
                  (4, ((0,-20), (3,-22), (6,-20), (9,-22), (12,-20)))], SideType.RIVER),
                ([(1, ((0,-20), (3,-22),)),
                  (2, ((0,-20), (3,-22), (6,-20),))], SideType.CROPS),
                ([(2, ((0,-20), (3,-22), (6,-20),)),
                  (3, ((0,-20), (3,-22), (6,-20), (9,-22),))], SideType.WOODS),
                ([(2, ((0,-20), (-3,-18), (-3,-14),))], SideType.WOODS),
                ([(3, ((0,-20), (-3,-18), (-3,-14), (-3,-10),))], SideType.CROPS),
                ([(4, ((0, -20), (3, -22), (6, -20), (9, -22), (12, -20)))], SideType.RIVER),
                ([(4, ((0, -20), (3, -22), (6, -20), (9, -22), (12, -20)))], SideType.WOODS),
                ([(4, ((0, -20), (-3, -18), (-3, -14), (-3, -10), (-3, -6)))], SideType.CROPS),
                ([(4, ((0, -20), (-3, -18), (-3, -14), (-3, -10), (-3, -6)))], SideType.HOUSE)
            ]
        },
        (999,999) : {  # invalid coordinate
            -1: [],
            0 : [],
            1 : [],
            2 : [],
            3 : []
        }
    }

    for coords, expected_perspective_group_types_hops in expectation.items():
        for hops, expected_perspective_group_types in expected_perspective_group_types_hops.items():
            perspective_groups = tile_evaluation.get_distant_groups(session.open_coords, coords, remaining_hops=hops)

            actual_perspective_group_types = [(list(distant_group_paths.keys()), session.groups[group_id].type)
                                              for group_id, distant_group_paths in perspective_groups.items() ]

            assert sorted(actual_perspective_group_types) == sorted(expected_perspective_group_types)

def test_get_perspective_group_extension_for_tile():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_extensions.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.PONDS, SideType.PONDS, SideType.CROPS, SideType.TRAIN, SideType.PONDS, SideType.PONDS],
        SideType.PONDS)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-20) : [
            [
                [SideType.PONDS, SideType.PONDS, SideType.CROPS, SideType.TRAIN, SideType.PONDS, SideType.PONDS],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 6)
                    ]]
                ]
            ],
            [
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.CROPS, SideType.TRAIN, SideType.PONDS],
                [
                    [SideType.RIVER, [
                        (SideType.RIVER, 3),
                        (SideType.CROPS, 0)
                    ]],
                    [SideType.CROPS, [
                        (SideType.CROPS, 1)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 5)
                    ]]
                ]
            ],
            [
                [SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.PONDS, SideType.CROPS, SideType.TRAIN],
                [
                    [SideType.RIVER, [
                        (SideType.RIVER, 3),
                        (SideType.CROPS, 0)
                    ]],
                    [SideType.CROPS, [
                        (SideType.CROPS, 2)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 4)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_neighbor_perspective_groups_multi_self():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_extensions.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.CROPS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.GREEN],
        SideType.GREEN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (15,-10) : [
            [
                [SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.CROPS, SideType.CROPS],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0),
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ],
            [
                [SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.CROPS],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0)
                    ]]
                ]
            ],
            [
                [SideType.CROPS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN, SideType.GREEN],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.CROPS, SideType.GREEN, SideType.GREEN],
                [
                    [SideType.CROPS, [
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.CROPS, SideType.GREEN],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.WOODS, 0),
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0),
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.CROPS],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.WOODS, 0),
                        (SideType.WOODS, 0),
                        (SideType.RIVER, 0),
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_neighbor_perspective_groups_restricted():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
        SideType.HOUSE)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (-6,-4) : [
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE],
                [
                    [SideType.RIVER, [
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1)
                    ]]
                ]
            ],
            [
                [SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER],
                [
                    [SideType.RIVER, [
                        (SideType.HOUSE, 0)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_consideration():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (-6,-4) : [
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE],
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER],
                [SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER]
            ],
            [
                # river blocks perspective
                [SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
        SideType.HOUSE)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_perspective_group_rating_mix():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_2.csv", simulate_tile_placement=False)

    # groups have same size, perspective group makes the difference
    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (-6,-4) : [
            [
                # perspective of size 1 in distance 3
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER],
                [SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER]
            ],
            [
                # perspectibe blocked by river
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE]
            ]
        ],
        (6,4) : [
            [
                # no perspective
                [SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
                [SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
                [SideType.HOUSE, SideType.HOUSE, SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE],
                [SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.RIVER]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.RIVER, SideType.RIVER, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
        SideType.HOUSE)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)

    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'group_rating')

def test_perspective_group_rating_crossing_restricted_same_tile():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_3.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.TRAIN, SideType.HOUSE, SideType.GREEN], SideType.TRAIN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-4) : [
            [
                [SideType.GREEN, SideType.TRAIN, SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.TRAIN],
                [
                    [SideType.TRAIN, [
                        (SideType.HOUSE, 0),
                        (SideType.WOODS, 0)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.TRAIN, SideType.HOUSE],
                [
                    [SideType.HOUSE, [
                        (SideType.WOODS, 0)
                    ]],
                    [SideType.WOODS, [
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ],
            [
                [SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.TRAIN, SideType.HOUSE, SideType.GREEN],
                [
                    [SideType.TRAIN, [
                        (SideType.HOUSE, 0)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.TRAIN, SideType.GREEN, SideType.TRAIN],
                [
                    [SideType.TRAIN, [
                        (SideType.WOODS, 0)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_distant_crossing_restricted():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_4.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.HOUSE, SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.WOODS],
        SideType.GREEN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-12) : [
            [
                [SideType.GREEN, SideType.HOUSE, SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.WOODS],
                [
                    [SideType.WOODS, [
                        (SideType.WOODS, 1)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1)
                    ]]
                ]
            ],
            [
                [SideType.WOODS, SideType.GREEN, SideType.HOUSE, SideType.HOUSE, SideType.GREEN, SideType.WOODS],
                [
                    [SideType.WOODS, [
                        (SideType.WOODS, 1)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 2)
                    ]]
                ]
            ],
            [
                [SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.HOUSE, SideType.HOUSE, SideType.GREEN],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 3)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.HOUSE, SideType.HOUSE],
                []
            ],
            [
                [SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.HOUSE],
                [
                    [SideType.WOODS, [
                        (SideType.WOODS, 3)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1)
                    ]],
                    [SideType.WOODS, [
                        (SideType.WOODS, 2)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_crossing_restricted():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_5.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.HOUSE], SideType.HOUSE)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (3,-6) : [
            [
                [SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE, SideType.HOUSE],
                [
                    [SideType.HOUSE, [
                        (SideType.TRAIN, 0)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_restricted_crossing_restricted():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_6.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.TRAIN],
        SideType.GREEN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-16) : [
            [
                [SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.TRAIN],
                [
                    [SideType.RIVER, [
                        (SideType.RIVER, 1)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 1)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.TRAIN],
                [
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 1)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.TRAIN, SideType.GREEN, SideType.RIVER],
                [
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_restricted_crossing_restricted_2():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_7.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.HOUSE, SideType.GREEN, SideType.HOUSE], SideType.HOUSE)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (3,2) : [
            [
                [SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.HOUSE, SideType.GREEN, SideType.HOUSE],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.CROPS, 1)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.TRAIN, 0)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.HOUSE, SideType.GREEN],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 0),
                        (SideType.CROPS, 0)
                    ]],
                    [SideType.CROPS, [
                        (SideType.TRAIN, 0),
                        (SideType.CROPS, 1),
                        (SideType.CROPS, 2)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.HOUSE, SideType.GREEN, SideType.CROPS, SideType.CROPS, SideType.HOUSE],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1),
                        (SideType.CROPS, 0)
                    ]],
                    [SideType.CROPS, [
                        (SideType.TRAIN, 0)
                    ]]
                ]
            ],
            [
                [SideType.HOUSE, SideType.GREEN, SideType.HOUSE, SideType.GREEN, SideType.CROPS, SideType.CROPS],
                [
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 0),
                        (SideType.CROPS, 0)
                    ]]
                ]
            ],
            [
                [SideType.CROPS, SideType.HOUSE, SideType.GREEN, SideType.HOUSE, SideType.GREEN, SideType.CROPS],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.CROPS, 1),
                        (SideType.HOUSE, 0)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 1),
                        (SideType.TRAIN, 0),
                        (SideType.CROPS, 0)
                    ]]
                ]
            ],
            [
                [SideType.CROPS, SideType.CROPS, SideType.HOUSE, SideType.GREEN, SideType.HOUSE, SideType.GREEN],
                [
                    [SideType.CROPS, [
                        (SideType.CROPS, 0),
                        (SideType.CROPS, 0),
                        (SideType.HOUSE, 0)
                    ]],
                    [SideType.HOUSE, [
                        (SideType.HOUSE, 2)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_restricted_crossing_restricted_3():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_8.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.RIVER, SideType.RIVER, SideType.GREEN, SideType.TRAIN, SideType.TRAIN],
        SideType.GREEN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-24) : [
            [
                [SideType.GREEN, SideType.RIVER, SideType.RIVER, SideType.GREEN, SideType.TRAIN, SideType.TRAIN],
                [
                    [SideType.RIVER, [
                        (SideType.PONDS, 1),
                        (SideType.RIVER, 3)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 3)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.TRAIN, SideType.TRAIN, SideType.GREEN, SideType.RIVER, SideType.RIVER],
                [
                    [SideType.RIVER, [
                        (SideType.PONDS, 1)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_restricted_crossing_restricted_4():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_8.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.TRAIN, SideType.TRAIN],
        SideType.GREEN)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-24) : [
            [
                [SideType.GREEN, SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.TRAIN, SideType.TRAIN],
                [
                    [SideType.PONDS, [
                        (SideType.PONDS, 1),
                        (SideType.RIVER, 3)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 3)
                    ]]
                ]
            ],
            [
                [SideType.GREEN, SideType.TRAIN, SideType.TRAIN, SideType.GREEN, SideType.PONDS, SideType.PONDS],
                [
                    [SideType.PONDS, [
                        (SideType.PONDS, 1)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 6)
                    ]]
                ]
            ],
            [
                [SideType.PONDS, SideType.GREEN, SideType.TRAIN, SideType.TRAIN, SideType.GREEN, SideType.PONDS],
                [
                    [SideType.PONDS, [
                        (SideType.PONDS, 1)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 5)
                    ]]
                ]
            ],
            [
                [SideType.PONDS, SideType.PONDS, SideType.GREEN, SideType.TRAIN, SideType.TRAIN, SideType.GREEN],
                [
                    [SideType.PONDS, [
                        (SideType.PONDS, 1),
                        (SideType.RIVER, 3)
                    ]],
                    [SideType.TRAIN, [
                        (SideType.TRAIN, 4)
                    ]]
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_perspective_group_rating_neighbor_restricted_crossing_restricted_5():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_restricted_8.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.STATION],
        SideType.STATION)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (0,-24) : [
            [
                [SideType.STATION, SideType.STATION, SideType.STATION, SideType.STATION, SideType.STATION, SideType.STATION],
                [
                ]
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_get_perspective_group_extension_for_tile_self_extension():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_extensions_self.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles([SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN], SideType.RIVER)

    expected_candidate_coordinate_perspective_groups = {
        # coordinates: pairs of expected side type sequence and expected extension for group participation of tile
        # per group participation, the expected groups of a compatible type are given with their expected distance from the tile
        (-27,-22) : [
            [
                [SideType.RIVER, SideType.GREEN, SideType.GREEN, SideType.RIVER, SideType.GREEN, SideType.GREEN],
                []
            ]
        ]
    }

    assert_perspective_groups(expected_candidate_coordinate_perspective_groups, candidate_tiles, session)

def test_two_side_placement():
    session = Session()
    session.load_from_csv("./tests/data/two_side_placement.csv", simulate_tile_placement=False)

    expected_candidate_coordinate_rating_groups = {
        # coordinates, side types of a candidate rotation ordered by their expected rating from high to low
        (3,-2) : [
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS]
            ]
        ],
        (3,2) : [
            [
                [SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN]
            ],
            [
                [SideType.WOODS, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS, SideType.GREEN]
            ],
            [
                [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS]
            ]
        ]
    }

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.GREEN, SideType.WOODS, SideType.WOODS],
        SideType.GREEN)
    rated_candidates = session.compute_tile_ratings(candidate_tiles)
    assert_rating_groups(expected_candidate_coordinate_rating_groups, rated_candidates, 'rating')
