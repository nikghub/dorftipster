from typing import List, Dict, Tuple

import numpy as np

from src.side import Side
from src.side_type import SideType
from src.tile_subsection import TileSubsection
from src.tile import Tile
from src.group import Group
from src.constants import Constants


class TileEvaluation:
    PERFECT_MATCH_DICT = {
        SideType.WOODS: [SideType.WOODS],
        SideType.HOUSE: [SideType.HOUSE],
        SideType.GREEN: [SideType.GREEN, SideType.PONDS, SideType.STATION],
        SideType.CROPS: [SideType.CROPS],
        SideType.PONDS: [
            SideType.PONDS,
            SideType.GREEN,
            SideType.STATION,
            SideType.RIVER,
        ],
        SideType.STATION: [
            SideType.STATION,
            SideType.GREEN,
            SideType.PONDS,
            SideType.RIVER,
            SideType.TRAIN,
        ],
        SideType.RIVER: [SideType.RIVER, SideType.PONDS, SideType.STATION],
        SideType.TRAIN: [SideType.TRAIN, SideType.STATION],
    }

    RESTRICTED_DICT = {
        SideType.RIVER: [SideType.RIVER, SideType.PONDS, SideType.STATION],
        SideType.TRAIN: [SideType.TRAIN, SideType.STATION],
    }

    # using the neighbor compatibilty score we can handle types
    # that are not covered by any other rating mechanism
    _DIRECT_NEIGHBOR_COMPATIBILITY_SCORE = [
        (
            1,
            {
                SideType.STATION: [SideType.RIVER, SideType.TRAIN],
                SideType.GREEN: [SideType.GREEN],
            },
        ),
        (
            0.5,
            {
                SideType.STATION: [SideType.STATION, SideType.PONDS],
                SideType.GREEN: [SideType.PONDS, SideType.STATION],
            },
        ),
        (
            -0.5,
            {
                SideType.STATION: [SideType.WOODS, SideType.HOUSE, SideType.CROPS]
            }
        ),
    ]
    _OTHER_NEIGHBOR_COMPATIBILITY_SCORE = [
        (
            1,
            {
                SideType.STATION: [SideType.RIVER, SideType.TRAIN],
                SideType.GREEN: [SideType.GREEN],
            },
        ),
        (
            0.5,
            {
                SideType.STATION: [SideType.STATION, SideType.PONDS],
                SideType.GREEN: [SideType.PONDS, SideType.STATION],
            },
        ),
        (
            -0.5,
            {
                SideType.STATION: [SideType.WOODS, SideType.HOUSE, SideType.CROPS]
            }
        ),
    ]

    _BASE_VALUE = 100

    _BASE_RATING = {
        Side.Placement.UNKNOWN_MATCH: {
            Tile.Placement.UNKNOWN: 0.15 * _BASE_VALUE
        },
        Side.Placement.IMPERFECT_MATCH: {
            Tile.Placement.PERFECT: -2.25 * _BASE_VALUE,
            Tile.Placement.IMPERFECT: -1.75 * _BASE_VALUE,
        },
        Side.Placement.PERFECT_MATCH: {
            Tile.Placement.IMPERFECT: 0.5 * _BASE_VALUE,
            Tile.Placement.PERFECT: _BASE_VALUE,
            Tile.Placement.PERFECTLY_CLOSED: 1.5 * _BASE_VALUE,
        },
    }

    _GROUP_SIZE_MIN_RATING = 0
    _GROUP_SIZE_MAX_RATING = 1.1 * _BASE_VALUE

    _GROUP_SIZE_BOOST_FACTOR = {
        # group of type that is extended, extension of group with tile side type -> size boostfactor
        SideType.PONDS : {
            SideType.PONDS : 2,
            SideType.STATION : 2,
            SideType.RIVER : 3
        },
        SideType.RIVER : {
            SideType.PONDS : 2,
            SideType.STATION : 2,
            SideType.RIVER : 3
        },
        SideType.TRAIN : {
            SideType.STATION : 3,
            SideType.TRAIN : 4.5
        }
    }

    # please note that the distance to reach any side of a direct neighbor is considered 0
    _PERSPECTIVE_GROUPS_MAX_DISTANCE_RESTRICTED_TYPES = 5
    _PERSPECTIVE_GROUPS_MAX_DISTANCE_NON_RESTRICTED_TYPES = 2

    _GROUP_SIZE_RATING_RESTRICTED_BOOST_FACTOR = 2.25

    _NEIGHBOR_GROUP_INTERFERENCE_RESTRICTED_BOOST_FACTOR = 2.25
    _NEIGHBOR_GROUP_INTERFERENCE_MIN_RATING = 0
    _NEIGHBOR_GROUP_INTERFERENCE_MAX_RATING = -0.2 * _BASE_VALUE

    _PLUG_HOLE_VALUE = 1 * _BASE_VALUE

    _TYPE_DEMOTION_RATING_VALUE = -1.25 * _BASE_VALUE

    _NEIGHBOR_COMPATIBILITY_MIN_RATING = -0.3 * _BASE_VALUE
    _NEIGHBOR_COMPATIBILITY_MAX_RATING = 0.4 * _BASE_VALUE

    _RESTRICTED_TYPE_ORIENTATION_MIN_RATING = 0
    _RESTRICTED_TYPE_ORIENTATION_MAX_RATING = 0.5 * _BASE_VALUE
    _RESTRICTED_TYPE_ORIENTATION_NUM_RINGS = 2

    def __init__(self, candidate_tiles, open_coords_per_candidate,
                 played_tiles, groups):
        self.rating_details: List[TileEvaluation.RatingDetails] = []
        if candidate_tiles is not None:
            for tile, open_coords in list(
                zip(candidate_tiles, open_coords_per_candidate)
            ):
                if tile.get_placement() != Tile.Placement.NOT_POSSIBLE:
                    self.rating_details.append(
                        TileEvaluation.RatingDetails(tile, played_tiles, open_coords)
                    )

        self.played_tiles = played_tiles

        # group id to group
        self.groups: Dict[str, Group] = groups

        # possible extension coordinates to list of group ids that may be extend at this coordinate
        # stored once in order to allow quick lookup by coordinates
        self.possible_group_extensions: Dict[Tuple[int, int], List[str]] = {}

        for group in self.groups.values():
            for coords in group.possible_extensions.keys():
                if coords not in self.possible_group_extensions:
                    self.possible_group_extensions[coords] = []
                self.possible_group_extensions[coords].append(group.id)

        self._prepare()
        self._compute()

    def get_rated_tiles(self):
        return sorted(
            [
                TileEvaluation.RatedTile(rating_detail)
                for rating_detail in self.rating_details
            ],
            key=lambda rd: rd.rating,
            reverse=True,
        )

    @staticmethod
    def compute_side_placement_match(side_type, opp_side_type):
        if SideType.UNKNOWN in [side_type, opp_side_type]:
            return Side.Placement.UNKNOWN_MATCH

        # some types only allow placement against certain types
        if (
            side_type in TileEvaluation.RESTRICTED_DICT
            and opp_side_type not in TileEvaluation.RESTRICTED_DICT[side_type]
        ) or (
            opp_side_type in TileEvaluation.RESTRICTED_DICT
            and side_type not in TileEvaluation.RESTRICTED_DICT[opp_side_type]
        ):
            return Side.Placement.NOT_POSSIBLE

        if opp_side_type in TileEvaluation.PERFECT_MATCH_DICT[side_type]:
            return Side.Placement.PERFECT_MATCH

        return Side.Placement.IMPERFECT_MATCH

    def get_distant_groups_for_tile(self, tile, open_coords):
        distant_groups = {}
        # iterate over all groups to hop from a group extending tile side over open tiles
        # to find groups that the given tile could build towards to
        for gp in tile.group_participation.values():
            considered_distant_groups = {}
            for subsection in gp.subsections:
                if subsection == TileSubsection.CENTER:
                    continue

                neighbor_coordinates = tile.get_neighbor_coords(subsection)
                # look at extensions for the group that are open from the candidate tile
                if neighbor_coordinates not in open_coords:
                    continue

                if Group.is_type_restricted(gp.group.type):
                    max_dist = self._PERSPECTIVE_GROUPS_MAX_DISTANCE_RESTRICTED_TYPES
                else:
                    max_dist = (
                        self._PERSPECTIVE_GROUPS_MAX_DISTANCE_NON_RESTRICTED_TYPES
                    )

                # possibly remove open tiles to hop onto
                local_open_tiles = dict(open_coords)
                for s in TileSubsection.get_side_values():
                    side_type = tile.get_side(s).type
                    coords = tile.get_neighbor_coords(s)
                    if coords not in local_open_tiles:
                        continue
                    if side_type not in self.RESTRICTED_DICT:
                        continue

                    # remove open tiles
                    # * that are incompatible directions (due to restricted types) for the given group
                    if side_type not in Constants.COMPATIBLE_GROUP_TYPES[gp.group.type]:
                        del local_open_tiles[coords]

                    # remove open tiles
                    # that are also of a restricted, compatible type
                    # as we expect to be able to connect to these compatible types,
                    # before we will reach a further away compatible type
                    elif s != subsection:
                        del local_open_tiles[coords]

                for distant_group_id, paths in self.get_distant_groups(
                    local_open_tiles,
                    neighbor_coordinates,
                    remaining_hops=max_dist - 1,
                    distance=0,
                ).items():
                    # same group should not be considered
                    if distant_group_id == gp.group.id:
                        continue

                    if distant_group_id in gp.group.consumed_groups:
                        continue

                    for dist, path_coords in paths:
                        if self._skip_path_to_group(
                            gp.group, self.groups[distant_group_id], dist, path_coords
                        ):
                            continue

                        # we might be able to reach the same group from multiple sides
                        # therefore only store closest distance
                        if (
                            distant_group_id not in considered_distant_groups
                            or dist < considered_distant_groups[distant_group_id][0]
                        ):
                            considered_distant_groups[distant_group_id] = (
                                dist,
                                tile.get_side(subsection).type,
                                1,
                            )
                        # track if we are able to connect to the same group
                        # from a different side with the same distance
                        elif dist == considered_distant_groups[distant_group_id][0]:
                            considered_distant_groups[distant_group_id] = (
                                dist,
                                tile.get_side(subsection).type,
                                considered_distant_groups[distant_group_id][2] + 1,
                            )

            if considered_distant_groups:
                distant_groups[gp.group.id] = considered_distant_groups

        return distant_groups

    def get_distant_groups(
        self,
        allowed_tiles,
        start_coordinate,
        remaining_hops=0,
        distance=0,
        neighboring_groups=None,
        visited_tiles=None,
    ):
        # helper method to insert
        def insert(container, g_id, dist, path):
            if g_id not in container:
                container[g_id] = {}

            insertion_tuple = (dist, tuple(path))
            container[g_id][insertion_tuple] = None

        if neighboring_groups is None:
            neighboring_groups = {}

        if visited_tiles is None:
            visited_tiles = {}

        if start_coordinate not in allowed_tiles or remaining_hops < 0:
            return neighboring_groups

        visited_tiles[start_coordinate] = remaining_hops

        if start_coordinate in self.possible_group_extensions:
            for group_id in self.possible_group_extensions[start_coordinate]:
                path_coords = list(visited_tiles.keys())
                insert(neighboring_groups, group_id, distance, path_coords)

        for subsection in TileSubsection.get_side_values():
            neighbor_coordinates = Tile.get_coordinates(start_coordinate, subsection)
            # only hop on allowed tiles
            if neighbor_coordinates not in allowed_tiles:
                continue

            # only hop if we either haven't been to the tile, or we have more hops left
            # than from another part that we entered the tile
            if (
                neighbor_coordinates in visited_tiles
                and remaining_hops < visited_tiles[neighbor_coordinates]
            ):
                continue

            # check which groups could possibly be extended
            # at the neighbor tile and save with their distance
            if neighbor_coordinates in self.possible_group_extensions:
                for group_id in self.possible_group_extensions[neighbor_coordinates]:
                    path_coords = list(visited_tiles.keys()) + [neighbor_coordinates]
                    insert(neighboring_groups, group_id, distance + 1, path_coords)

            if remaining_hops >= 1:
                local_visited_tiles = dict(visited_tiles)
                self.get_distant_groups(
                    allowed_tiles,
                    neighbor_coordinates,
                    remaining_hops - 1,
                    distance + 1,
                    neighboring_groups,
                    local_visited_tiles,
                )

        return neighboring_groups

    def get_surrounding_tiles(self, center_coord, num_rings=2):
        neighboring_tiles = {}

        if num_rings < 1:
            if center_coord in self.played_tiles:
                return {center_coord: self.played_tiles[center_coord]}

            return {}

        # look at all neighbor tiles
        for subsection in TileSubsection.get_all_values():
            coord = Tile.get_coordinates(center_coord, subsection)
            if coord in self.played_tiles:
                neighboring_tiles[coord] = self.played_tiles[coord]

            neighboring_tiles.update(self.get_surrounding_tiles(coord, num_rings - 1))

        return neighboring_tiles

    def _skip_path_to_group(self, origin_group, distant_group, dist, path_coords):
        # distant groups of a different type will only be collected if they are direct neighbors
        if (
            distant_group.type not in Constants.COMPATIBLE_GROUP_TYPES[origin_group.type]
            and dist > 0
        ):
            return True

        for i, coord in enumerate(path_coords):
            # search for path coordinates that intersect with other groups possible extension points
            if coord not in self.possible_group_extensions:
                continue

            for group_id in self.possible_group_extensions[coord]:
                # do not consider any extension to a group that "crosses" a restricted type
                # as a restricted type will definitively block the extension
                crossing_group_type = self.groups[group_id].type
                if crossing_group_type not in self.RESTRICTED_DICT:
                    continue

                # skip paths were the destination groups
                # are not directly adjacent to the direct open neighbor tile and
                # * origin and crossing group are of incompatible types
                # * origin and crossing group are compatible types
                #   but we are not the last coordinate in the paths
                is_last_coord = i == len(path_coords) - 1
                if (
                    crossing_group_type
                    not in Constants.COMPATIBLE_GROUP_TYPES[origin_group.type]
                    or not is_last_coord
                ) and dist > 0:
                    return True

        return False

    def _prepare(self):
        for r in self.rating_details:
            self._prepare_neighbor_compatibility_score(r)
            self._prepare_group_aggregation(r)
            self._prepare_restricted_type_orientation_score(r)
            self._prepare_distant_group_consideration(r)

    def _prepare_neighbor_compatibility_score(self, rating):
        def get_side_types(subsection, n_subsection):
            if (
                n_subsection not in rating.open_neighbor_side_types[subsection]
                or rating.open_neighbor_side_types[subsection][n_subsection]
                == SideType.UNKNOWN
                or n_subsection == Tile.get_opposing(subsection)
            ):
                return (None, None)

            return (
                rating.open_neighbor_side_types[subsection][
                    Tile.get_opposing(subsection)
                ],
                rating.open_neighbor_side_types[subsection][n_subsection],
            )

        def get_score(score_list, subsection, n_subsection):
            side_type, n_side_type = get_side_types(subsection, n_subsection)
            if side_type is not None and n_side_type is not None:
                for score, side_types_container in score_list:
                    # score applies both ways (bidirectional)
                    if (
                        side_type in side_types_container
                        and n_side_type in side_types_container[side_type]
                    ) or (
                        n_side_type in side_types_container
                        and side_type in side_types_container[n_side_type]
                    ):
                        return score
            return 0

        rating.neighbor_compatibility_score = 0
        for subsection in TileSubsection.get_all_values():
            if subsection not in rating.open_neighbor_side_types:
                # neighbor tile is not open
                continue

            direct_neighbor_subsections = Tile.get_direct_neighbors(
                Tile.get_opposing(subsection)
            )
            for n_subsection in TileSubsection.get_side_values():
                if n_subsection in direct_neighbor_subsections:
                    score_list = self._DIRECT_NEIGHBOR_COMPATIBILITY_SCORE
                else:
                    score_list = self._OTHER_NEIGHBOR_COMPATIBILITY_SCORE
                rating.neighbor_compatibility_score += get_score(
                    score_list, subsection, n_subsection
                )

    def _prepare_group_aggregation(self, rating):
        total_size = 0
        extension_group_types = []
        for gp in rating.tile.group_participation.values():
            # extended existing groups are considered with their full size (full bonus)
            factor = 1.0
            # restricted type groups get an additional bonus
            # as tiles for these groups are less frequent
            if Group.is_type_restricted(gp.group.type):
                # side type of the tile with which we extend the group
                extension_type = rating.tile.get_side(gp.subsections[0]).type
                factor = self._GROUP_SIZE_BOOST_FACTOR[gp.group.type][extension_type]

            if gp.group.id in self.groups:
                # keep track of group types that are extended by the candidate tile
                extension_group_types.append(gp.group.type)
            else:
                if len(gp.group.possible_extensions) > 0:
                    # a new group that does not extend any existing
                    # is considered with its half size (smaller bonus)
                    factor *= 0.5
                else:
                    # a new group that is created but directly closed receives only a tiny bonus
                    factor *= 0.1

            total_size += factor * gp.group.size

        rating.group_aggregation = (total_size, list(set(extension_group_types)))

    def _prepare_restricted_type_orientation_score(self, rating):
        rating.rt_extension_surrounding_tile_count = 0
        for gp in rating.tile.group_participation.values():
            if not Group.is_type_restricted(gp.group.type):
                continue

            for subsection in gp.subsections:
                if subsection == TileSubsection.CENTER:
                    continue

                # types that may be equivalent to green regarding placement should be ignored
                if SideType.is_equivalent_to_green(
                    rating.tile.get_side(subsection).type
                ):
                    continue

                neighbor_coordinates = rating.tile.get_neighbor_coords(subsection)
                # look at extensions for the group that are open from the candidate tile
                if any(
                    neighbor_coordinates in container
                    for container in [gp.group.tile_coordinates, self.played_tiles]
                ):
                    continue

                rating.rt_extension_surrounding_tile_count += len(
                    self.get_surrounding_tiles(
                        neighbor_coordinates,
                        num_rings=self._RESTRICTED_TYPE_ORIENTATION_NUM_RINGS,
                    )
                )

    def _prepare_distant_group_consideration(self, rating):
        rating.perspective_group_extension_score = 0
        rating.neighbor_group_interference_score = 0

        max_dist = max(
            self._PERSPECTIVE_GROUPS_MAX_DISTANCE_RESTRICTED_TYPES,
            self._PERSPECTIVE_GROUPS_MAX_DISTANCE_NON_RESTRICTED_TYPES,
        )
        for distant_groups in self.get_distant_groups_for_tile(
            rating.tile, rating.open_coords
        ).values():
            for distant_group_id, (
                distance,
                extension_type,
                num_sides,
            ) in distant_groups.items():
                distant_group = self.groups[distant_group_id]
                factor = 1.0

                if distant_group.type in Constants.COMPATIBLE_GROUP_TYPES[extension_type]:
                    # boost restricted type extension
                    if Group.is_type_restricted(distant_group.type):
                        factor = self._GROUP_SIZE_BOOST_FACTOR[distant_group.type][
                            extension_type
                        ]

                    # scale the group size to receive
                    #  * the full size (distance_factor: 1)
                    #    for the direct neighbor group (distance == 0)
                    #  * half the size (distance_factor: 0.5)
                    #    for the neighbor at distance == 1
                    #  * the smallest size (factor: 1 / max_dist)
                    #    for the furthest away group (distance == max_dist)
                    if distance == 0:
                        distance_factor = 1.0
                    else:
                        min_dist_factor = 1 / max_dist
                        distance_factor = min_dist_factor + (0.5 - min_dist_factor) * (
                            1 - ((distance - 1) / (max_dist - 1))
                        )

                    factor *= distance_factor
                    rating.perspective_group_extension_score += (
                        factor * distant_group.size
                    )
                elif distance == 0:
                    if (
                        distant_group.type in self.RESTRICTED_DICT
                        or extension_type in self.RESTRICTED_DICT
                    ):
                        factor = (
                            self._NEIGHBOR_GROUP_INTERFERENCE_RESTRICTED_BOOST_FACTOR
                        )
                    factor *= num_sides
                    rating.neighbor_group_interference_score += (
                        factor * distant_group.size
                    )

    def _compute(self):
        def get_min_max(container):
            sorted_container = sorted(container, reverse=True)
            return (
                [sorted_container[pos] for pos in [-1, 0]] if sorted_container else None
            )

        group_min_max = get_min_max(
            [
                r.group_aggregation[0] + r.perspective_group_extension_score
                for r in self.rating_details
            ]
        )
        neighbor_compatibility_min_max = get_min_max(
            [r.neighbor_compatibility_score for r in self.rating_details]
        )
        restricted_type_orientation_min_max = get_min_max(
            [r.rt_extension_surrounding_tile_count for r in self.rating_details]
        )
        interference_group_min_max = get_min_max(
            [r.neighbor_group_interference_score for r in self.rating_details]
        )

        for r in self.rating_details:
            self._compute_tile_placement_rating(r)
            self._compute_group_sizes_rating(r, group_min_max)
            self._compute_neighbor_type_demotion_rating(r)
            self._compute_neighbor_compatibility_rating(
                r, neighbor_compatibility_min_max
            )
            self._compute_restricted_type_orientation(
                r, restricted_type_orientation_min_max
            )
            self._compute_group_interference_rating(r, interference_group_min_max)

    def _compute_normalized_rating(
        self, val_min_max, value, rating_min_max, boost_factor=1.0, invert=False
    ):
        min_val, max_val = val_min_max
        if min_val == max_val:
            return 0  # rating should not be considered at all as all tiles have the same value

        normalized_factor = (value - min_val) / (max_val - min_val)
        if invert:
            normalized_factor = 1 - normalized_factor

        min_rating, max_rating = rating_min_max
        return int(
            min_rating + normalized_factor * boost_factor * (max_rating - min_rating)
        )

    def _compute_tile_placement_rating(self, rating):
        rating.tile_placement_rating = 0
        for subsection in TileSubsection.get_side_values():
            neighbor_coords = rating.tile.get_neighbor_coords(subsection)
            tile_placement = Tile.Placement.UNKNOWN

            side = rating.tile.get_side(subsection)
            if neighbor_coords in self.played_tiles:
                neigbor_tile = self.played_tiles[neighbor_coords]
                if side.placement == Side.Placement.IMPERFECT_MATCH:
                    # when placing imperfectly, consider if the neighboring tile
                    # that we place against has already been imperfect before or
                    # would only be ruined through the candidate tile
                    tile_placement = neigbor_tile.get_placement()
                elif side.placement == Side.Placement.PERFECT_MATCH:
                    # when placing perfectly, see if the neighboring tile that we place against
                    # would be perfectly closed by the candidate tile
                    tile_placement = (
                        neigbor_tile.get_placement_considering_neighbor_tile(
                            rating.tile
                        )
                    )

            rating.tile_placement_rating += self._BASE_RATING[side.placement][
                tile_placement
            ]

        # assign a bonus, if the candidate is directly closed and therefore plugs a hole
        if rating.tile.get_num_sides(Side.Placement.UNKNOWN_MATCH) == 0:
            rating.tile_placement_rating += self._PLUG_HOLE_VALUE

    def _compute_group_sizes_rating(self, rating, min_max_group_size):
        total_group_size, involved_group_types = rating.group_aggregation

        # we combine the group size (actual group size increase) with the
        # perspective group size increase to calculate the group rating
        total_group_size += rating.perspective_group_extension_score

        boost_factor = 1.0
        # boost groups of restricted types as extending them
        # should be a priority as restricted type tiles are rare
        if any(
            Group.is_type_restricted(involved_type)
            for involved_type in involved_group_types
        ):
            boost_factor = self._GROUP_SIZE_RATING_RESTRICTED_BOOST_FACTOR

        rating.group_rating = self._compute_normalized_rating(
            min_max_group_size,
            total_group_size,
            (self._GROUP_SIZE_MIN_RATING, self._GROUP_SIZE_MAX_RATING),
            boost_factor=boost_factor,
        )

    def _compute_neighbor_type_demotion_rating(self, rating):
        rating.neighbor_type_demotion_rating = 0
        for subsection in TileSubsection.get_all_values():
            if subsection not in rating.open_neighbor_side_types:
                continue

            num_known_sides = 0
            num_station_compatible_sides = 0
            different_types = {}  # actual different types
            different_types_reduced = []  # compatibility considered
            for n_subsection, n_type in rating.open_neighbor_side_types[
                subsection
            ].items():
                if n_type == SideType.UNKNOWN:
                    continue
                if subsection == Tile.get_opposing(n_subsection):
                    continue

                num_known_sides += 1

                different_types[n_type] = None
                if not any(
                    n_type in self.PERFECT_MATCH_DICT[known_type]
                    for known_type in different_types_reduced
                ):
                    different_types_reduced.append(n_type)

                if (
                    SideType.is_equivalent_to_green(n_type)
                    or n_type in self.RESTRICTED_DICT
                ):
                    num_station_compatible_sides += 1

            if len(different_types) == 0:
                continue

            side = rating.tile.get_side(subsection)

            # there are no tiles with more than 4 different types
            # therefore apply a demotion if the candidate tile would add a new type,
            # thereby exceeding the threshold
            if len(different_types_reduced) > 3 and not any(
                side.type in self.PERFECT_MATCH_DICT[known_type]
                for known_type in different_types_reduced
            ):
                rating.neighbor_type_demotion_rating += self._TYPE_DEMOTION_RATING_VALUE

            # if the candidate tile would introduce a restricted type that is not yet present
            # for the open tile, we know that only a station will perfectly match there
            # therefore apply a demotion if a station would not perfectly match the open tile
            if (
                any(
                    restricted_type in different_types
                    for restricted_type in self.RESTRICTED_DICT
                )
                and side.type in self.RESTRICTED_DICT
                and side.type not in different_types
                and num_station_compatible_sides < num_known_sides
            ):
                rating.neighbor_type_demotion_rating += self._TYPE_DEMOTION_RATING_VALUE

            # if the open tile that the candidate side faces contains a restricted type, apply a
            # demotion as we usually want to avoid blocking restricted types in their extension
            # we are not considering the intersection of two different restricted types here as this
            # is already covered by the evaluation above
            elif (
                side.type in self.RESTRICTED_DICT
                and not any(
                    restricted_type in different_types
                    for restricted_type in self.RESTRICTED_DICT
                )
                and not any(
                    side.type in self.PERFECT_MATCH_DICT[known_type]
                    for known_type in different_types
                )
            ):
                # scale by the number of known sides, as it gets increasingly difficult to
                # extend the restricted type, the fewer options we have
                rating.neighbor_type_demotion_rating += (
                    self._TYPE_DEMOTION_RATING_VALUE * (num_known_sides / 5)
                )
            elif (
                side.type not in self.RESTRICTED_DICT
                and any(
                    restricted_type in different_types
                    for restricted_type in self.RESTRICTED_DICT
                )
                and not any(
                    side.type in self.PERFECT_MATCH_DICT[known_type]
                    for known_type in different_types
                    if known_type in self.RESTRICTED_DICT
                )
            ):
                # scale by the number of known sides, as it gets increasingly difficult to
                # extend the restricted type, the fewer options we have
                rating.neighbor_type_demotion_rating += (
                    self._TYPE_DEMOTION_RATING_VALUE * (num_known_sides / 5)
                )

    def _compute_neighbor_compatibility_rating(
        self, rating, min_max_neighbor_compatibility_score
    ):
        if rating.tile.get_num_sides(Side.Placement.UNKNOWN_MATCH) == 0:
            rating.neighbor_compatibility_rating = 0
            return

        rating.neighbor_compatibility_rating = self._compute_normalized_rating(
            min_max_neighbor_compatibility_score,
            rating.neighbor_compatibility_score,
            (
                self._NEIGHBOR_COMPATIBILITY_MIN_RATING,
                self._NEIGHBOR_COMPATIBILITY_MAX_RATING,
            ),
        )

    def _compute_restricted_type_orientation(
        self, rating, min_max_played_neighbor_count
    ):
        """
        Checks the groups that the candidate tile participates in and counts the played tiles
        in the surrounding area of all possible extensions.
        Only applies for restricted types, as we usually try to build away from other types
        to keep as many options open as possible.
        """
        rating.restricted_type_orientation_rating = self._compute_normalized_rating(
            min_max_played_neighbor_count,
            rating.rt_extension_surrounding_tile_count,
            (
                self._RESTRICTED_TYPE_ORIENTATION_MIN_RATING,
                self._RESTRICTED_TYPE_ORIENTATION_MAX_RATING,
            ),
            invert=True,
        )

    def _compute_group_interference_rating(
        self, rating, min_max_neighbor_group_interference_score
    ):
        rating.neighbor_group_interference_rating = self._compute_normalized_rating(
            min_max_neighbor_group_interference_score,
            rating.neighbor_group_interference_score,
            (
                self._NEIGHBOR_GROUP_INTERFERENCE_MIN_RATING,
                self._NEIGHBOR_GROUP_INTERFERENCE_MAX_RATING,
            ),
        )

    class RatingDetails:
        def __init__(self, candidate_tile, played_tiles, open_coords):
            # tile that we are evaluating
            self.tile: Tile = candidate_tile

            # open coords around all played_tiles,
            # assuming that the candidate tile would have been played already
            self.open_coords = open_coords

            # AGGREGATED INFORMATION
            # --------------------------------

            # aggregated information of all the groups
            # that the candidate tile participates in, consisting of:
            # 1) the sum of the sizes of groups that this tile connects to including the size
            #    extension to the respective groups, that would occur if the tile would be placed
            # 2) the types of the groups that are extended by the candidate tile
            self.group_aggregation: Tuple[int, List[SideType]] = None

            # if the candidate tile contains sides that are of a restricted type, we will look at
            # the open neighboring tile position of all restricted type outgoing sides and will
            # compute the number of played tiles that are in the nearby surrounding
            # for all of these open neighboring tiles and will store the sum in this variable
            self.rt_extension_surrounding_tile_count: int = 0

            # scores the compatibility of each side of the candidate tile
            # with respect to the known opposite side types of the neighboring open tile
            self.neighbor_compatibility_score: int = 0

            # sum of all distant group sizes, multiplied by a factor based on how far away they are,
            # that the candidate tile might possibly build towards to extend a group in the future
            self.perspective_group_extension_score: int = 0

            # sum of all groups that are directly neighboring any open tile that is adjacent to any
            # of the sides of the candidate tile
            self.neighbor_group_interference_score: int = 0

            # RATINGS
            # -------
            # evaluates the placement of the candidate tile regarding unknown,
            # imperfect or perfect placement of sides
            self.tile_placement_rating = 0

            # evalues the participation of the candidate in
            # (existing) groups and the increase of the group sizes
            self.group_rating = 0

            # evaluates open neighboring tiles at the candidate tile sides
            # and considers all adjacent types of the open tiles
            # regarding their compatibility with the candidate tile sides
            self.neighbor_compatibility_rating = 0

            # evaluates whether the candidate tile side types introduce a "tricky" situation,
            # that makes future play difficult. In that case, a demotion will be applied
            self.neighbor_type_demotion_rating = 0

            # evaluates the orientation of restricted types
            # within the candidate tile to prefer building restricted
            # types towards more open spaces, rather than towards existing tile placements
            self.restricted_type_orientation_rating = 0

            # evaluates whether a candidate tile interferes with a group of a different type
            # that is neighboring an open tile that is adjacent to the candidate tile
            # tries to avoid positioning tiles in a way that they block other groups
            self.neighbor_group_interference_rating = 0

            self.open_neighbor_side_types = self._prepare_neighbor_evaluation(
                played_tiles
            )

        def _prepare_neighbor_evaluation(self, played_tiles):
            # collect open neighbor tile side information
            open_neighbor_side_types: Dict[
                TileSubsection, Dict[TileSubsection, SideType]
            ] = {}
            for subsection in TileSubsection.get_side_values():
                neighbor_coordinate = self.tile.get_neighbor_coords(subsection)
                if neighbor_coordinate in played_tiles:
                    # neighbor tile is not open
                    continue

                open_neighbor_side_types[subsection] = {}

                # collect the side type of the opposing side and store it as
                # side type for the hypothetical neighboring tile
                for neighbor_subsection in TileSubsection.get_side_values():
                    opposing_subsection = Tile.get_opposing(neighbor_subsection)

                    opposing_tile_coordinate = Tile.get_coordinates(
                        neighbor_coordinate, neighbor_subsection
                    )
                    opposing_tile_side_type = SideType.UNKNOWN
                    if opposing_tile_coordinate in played_tiles:
                        opposing_tile_side_type = (
                            played_tiles[opposing_tile_coordinate]
                            .get_side(opposing_subsection)
                            .type
                        )
                    elif opposing_tile_coordinate == self.tile.coordinates:
                        opposing_tile_side_type = self.tile.get_side(
                            opposing_subsection
                        ).type

                    open_neighbor_side_types[subsection][
                        neighbor_subsection
                    ] = opposing_tile_side_type

            return open_neighbor_side_types

    class RatedTile:
        INVALID_RATING = np.iinfo(np.int32).min

        def __init__(self, rating_detail):
            self.tile: Tile = rating_detail.tile
            self.rating_detail = rating_detail
            self.rating: int = (
                rating_detail.tile_placement_rating
                + rating_detail.group_rating
                + rating_detail.neighbor_compatibility_rating
                + rating_detail.neighbor_type_demotion_rating
                + rating_detail.restricted_type_orientation_rating
                + rating_detail.neighbor_group_interference_rating
            )

        def __eq__(self, other):
            if isinstance(other, TileEvaluation.RatedTile):
                return self.tile == other.tile and self.rating == other.rating
            return False
