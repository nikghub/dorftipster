from enum import Enum
from typing import Dict, List, Tuple, Optional
from functools import lru_cache

from src.tile_subsection import TileSubsection
from src.side import Side
from src.side_type import SideType
from src.constants import Constants

class Tile:
    _opposite_dict = {
        TileSubsection.TOP: TileSubsection.BOTTOM,
        TileSubsection.UPPER_RIGHT: TileSubsection.LOWER_LEFT,
        TileSubsection.LOWER_RIGHT: TileSubsection.UPPER_LEFT,
        TileSubsection.BOTTOM: TileSubsection.TOP,
        TileSubsection.LOWER_LEFT: TileSubsection.UPPER_RIGHT,
        TileSubsection.UPPER_LEFT: TileSubsection.LOWER_RIGHT,
    }

    class Placement(Enum):
        UNKNOWN = -2
        NOT_POSSIBLE = -1
        IMPERFECT = 0
        PERFECT = 1
        PERFECTLY_CLOSED = 2

    class GroupParticipation:
        def __init__(self, group, subsections):
            self.group = group
            self.subsections: List[TileSubsection] = subsections

    def __init__(self, side_types, center_type, coordinates):
        self._subsections = Tile.extract_subsection_sides(side_types)
        self._subsections[TileSubsection.CENTER] = Side(
            SideType.extract_type(center_type)
        )

        self.coordinates: Tuple[int, int] = coordinates
        self.quest = None
        self.group_participation: Dict[str, Tile.GroupParticipation] = {}
        # store locally as optimization
        self._neighbor_coordinates = {}
        if self.coordinates is not None:
            self._neighbor_coordinates = {
                TileSubsection.TOP: (coordinates[0], coordinates[1] + 4),
                TileSubsection.UPPER_RIGHT: (coordinates[0] + 3, coordinates[1] + 2),
                TileSubsection.LOWER_RIGHT: (coordinates[0] + 3, coordinates[1] - 2),
                TileSubsection.BOTTOM: (coordinates[0], coordinates[1] - 4),
                TileSubsection.LOWER_LEFT: (coordinates[0] - 3, coordinates[1] - 2),
                TileSubsection.UPPER_LEFT: (coordinates[0] - 3, coordinates[1] + 2),
                TileSubsection.CENTER: (coordinates[0], coordinates[1]),
            }
        self._connected_subsection_groups = self._compute_connected_subsection_groups()

    def __eq__(self, other):
        if isinstance(other, Tile):
            return (
                self._subsections == other._subsections
                and self.coordinates == other.coordinates
            )
        return False

    def __lt__(self, other):
        return self.coordinates < other.coordinates

    @classmethod
    def extract_subsection_sides(cls, input):
        def check_isolated_same_type(side, other_side):
            if (
                side is not None
                and other_side is not None
                and (side.isolated or other_side.isolated)
                and side.type == other_side.type
            ):
                raise ValueError(
                    "An isolated side type can never have the same side type as neighbor"
                )

        if input is None:
            raise ValueError("Invalid input - None")

        sides: Dict[TileSubsection, Side] = {}

        if isinstance(input, SideType):
            input = [input]
        # single type for all may never be isolated
        elif (
            isinstance(input, str)
            and len(input) == 3
            and input[0] == "("
            and input[2] == ")"
        ):
            input = input[1]

        # ensure we always expand to all six sides
        if len(input) == 1:
            input = input * 6

        if isinstance(input, list):
            if len(input) != 6:
                raise ValueError(
                    "Expecting either a single type or 6 types for all sides"
                )

            for i, subsection in enumerate(TileSubsection.get_side_values()):
                if isinstance(input[i], SideType):
                    sides[subsection] = Side(input[i], False)
                elif isinstance(input[i], Side):
                    sides[subsection] = Side(input[i].type, input[i].isolated)
                else:
                    raise ValueError("Unexpected type in list")
        elif isinstance(input, str):
            i = 0
            prev_side = None
            side_subsections = TileSubsection.get_side_values()
            for subsection in side_subsections:
                if i >= len(input):
                    raise ValueError(
                        "Expecting either a single type or 6 types for all sides"
                    )

                if input[i] == "(":
                    if i + 2 >= len(input) or input[i + 2] != ")":
                        raise ValueError(
                            "Expecting exactly one character between '(' and ')'"
                        )
                    sides[subsection] = Side(
                        SideType.from_character(input[i + 1]), True
                    )
                    i += 3  # Move past the current pair of brackets and the character in between
                else:
                    sides[subsection] = Side(SideType.from_character(input[i]), False)
                    i += 1  # Move to the next character

                check_isolated_same_type(prev_side, sides[subsection])
                prev_side = sides[subsection]

            if i < len(input):
                raise ValueError(
                    "Expecting either a single type or 6 types for all sides"
                )

            # check last
            check_isolated_same_type(
                sides[side_subsections[0]], sides[side_subsections[-1]]
            )

        return sides

    @classmethod
    def is_valid_side_sequence(cls, sequence):
        try:
            cls.extract_subsection_sides(sequence)
        except ValueError:
            return False

        return True

    def get_center(self) -> Side:
        return self._subsections[TileSubsection.CENTER]

    def get_side(self, subsection: TileSubsection) -> Side:
        return self._subsections[subsection]

    def get_neighbor_coords(self, subsection):
        return self._neighbor_coordinates[subsection]

    def get_neighbor_coords_values(self):
        # return an immutable sequence of neighbor coordinate tuples
        return tuple(self._neighbor_coordinates.values())

    def create_all_orientations(self, include_self=True):
        orientations = []

        # collect all permutations of the sequence
        sides = []
        for subsection in TileSubsection.get_side_values():
            side = self.get_side(subsection)
            sides.append(Side(side.type, side.isolated))

        for i in range(len(sides)):
            rotated_sides = sides[i:] + sides[:i]
            if rotated_sides != sides or include_self:
                rotated_tile = Tile(
                    side_types=rotated_sides,
                    center_type=self.get_center().type,
                    coordinates=self.coordinates,
                )
                if rotated_tile not in orientations:
                    orientations.append(rotated_tile)
        return orientations

    def get_rotations(self):
        return self.create_all_orientations(include_self=False)

    def get_side_type_seq(self):
        seq = ""
        for subsection in TileSubsection.get_side_values():
            side = self.get_side(subsection)
            if side.isolated:
                seq += "(" + side.type.to_character() + ")"
            else:
                seq += side.type.to_character()
        return seq

    def get_placement(self):
        return self._get_placement_for_subsections(self._get_subsection_placements())

    def get_placement_considering_neighbor_tile(self, neighbor_tile):
        return self._get_placement_for_subsections(
            self._get_subsection_placements(neighbor_tile)
        )

    def get_num_sides(self, side_placement):
        return self._get_num_sides(self._get_subsection_placements(), side_placement)

    def get_num_perfectly_closed(self, played_tiles):
        num_perfectly_closed = 0
        for subsection in TileSubsection.get_side_values():
            side = self.get_side(subsection)
            neighbor_coords = self.get_neighbor_coords(subsection)
            if neighbor_coords not in played_tiles:
                continue
            neigbor_tile = played_tiles[neighbor_coords]
            if (
                side.placement == Side.Placement.PERFECT_MATCH
                and neigbor_tile.get_placement_considering_neighbor_tile(self)
                == Tile.Placement.PERFECTLY_CLOSED
            ):
                num_perfectly_closed += 1

        if self.get_num_sides(Side.Placement.PERFECT_MATCH) == 6:
            num_perfectly_closed += 1

        return num_perfectly_closed

    @classmethod
    @lru_cache(maxsize=None)
    def get_coordinates(cls, base_coordinates, subsection):
        x, y = base_coordinates
        if subsection == TileSubsection.TOP:
            return (x, y + 4)
        if subsection == TileSubsection.UPPER_RIGHT:
            return (x + 3, y + 2)
        if subsection == TileSubsection.LOWER_RIGHT:
            return (x + 3, y - 2)
        if subsection == TileSubsection.BOTTOM:
            return (x, y - 4)
        if subsection == TileSubsection.LOWER_LEFT:
            return (x - 3, y - 2)
        if subsection == TileSubsection.UPPER_LEFT:
            return (x - 3, y + 2)

        return (x, y)

    @classmethod
    @lru_cache(maxsize=None)
    def get_opposing(cls, subsection: TileSubsection) -> Optional[TileSubsection]:
        if subsection.value in cls._opposite_dict:
            return cls._opposite_dict[subsection]
        return None

    @classmethod
    @lru_cache(maxsize=None)
    def get_direct_neighbors(cls, subsection):
        if subsection == TileSubsection.CENTER:
            return []
        start_idx = TileSubsection.get_index(subsection)
        return [
            TileSubsection.at_index(start_idx + 1),
            TileSubsection.at_index(start_idx - 1),
        ]

    def _get_placement_for_subsections(self, subsections):
        if self._get_num_sides(subsections, Side.Placement.NOT_POSSIBLE) > 0:
            return self.Placement.NOT_POSSIBLE
        if self._get_num_sides(subsections, Side.Placement.IMPERFECT_MATCH) > 0:
            return self.Placement.IMPERFECT

        if self._get_num_sides(subsections, Side.Placement.UNKNOWN_MATCH) > 0:
            return self.Placement.PERFECT

        return self.Placement.PERFECTLY_CLOSED

    def _get_num_sides(self, side_placements, side_placement):
        return sum(
            [
                1 if placement == side_placement else 0
                for placement in side_placements.values()
            ]
        )

    def _get_subsection_placements(self, neighbor_tile=None):
        subsection_placements = {
            sub: self.get_side(sub).placement for sub in TileSubsection.get_side_values()
        }
        if neighbor_tile is not None:
            for subsection in TileSubsection.get_side_values():
                # update with the placement of the candidate tile
                if self.get_neighbor_coords(subsection) == neighbor_tile.coordinates:
                    subsection_placements[subsection] = neighbor_tile.get_side(
                        Tile.get_opposing(subsection)
                    ).placement
                    break
        return subsection_placements

    def get_connected_subsection_groups(self) -> List[Tuple[SideType, List[TileSubsection]]]:
        return self._connected_subsection_groups

    def _compute_connected_subsection_groups(self) -> List[Tuple[SideType, List[TileSubsection]]]:
        """
        Returns all of the subsection groups for the tile. That is:
        All subsections that are connected and have a type that is compatible with groups.

        Returns:
            A list of pairs, where each pair consists of
            the shared type and the corresponding subsections.
            Note that there may be multiple groups for the same type (if they are not connected).
        """
        subsection_groups = []
        center_type = self.get_center().type
        if center_type in Constants.COMPATIBLE_GROUP_TYPES:
            # we may reach all sides of the tile through the center,
            # therefore return all subsections where the side type matches the center type
            # and the side is not marked as isolated
            center_group = []

            for s in TileSubsection.get_all_values():
                side = self.get_side(s)
                if side.type == center_type and not side.isolated:
                    center_group.append(s)
            # only add center group if at least one side is involved,
            # otherwise the group can't ever be extended
            if len(center_group) > 1:
                subsection_groups.append((center_type, center_group))
            remaining_subsections =\
                [s for s in TileSubsection.get_side_values() if s not in center_group]
        else:
            remaining_subsections = list(TileSubsection.get_side_values())

        while len(remaining_subsections) > 0:
            start_subsection = remaining_subsections[0]
            start_idx = TileSubsection.get_index(start_subsection)
            side_type = self.get_side(start_subsection).type
            if side_type not in Constants.COMPATIBLE_GROUP_TYPES:
                del remaining_subsections[0]
                continue

            # iterate clockwise and counter clockwise
            # to collect connected subsections of sides where the type matches
            subsections = list(set(
                [start_subsection] + \
                self._iterate_subsection_sides(side_type, start_idx, start_idx+1) + \
                self._iterate_subsection_sides(side_type, start_idx, start_idx-1)
                ))
            subsection_groups.append((side_type, subsections))

            remaining_subsections = [s for s in remaining_subsections if s not in subsections]

        return subsection_groups

    def _iterate_subsection_sides(self, side_type, start_idx, curr_idx):
        subsection = TileSubsection.at_index(curr_idx)
        if self.get_side(subsection).type in Constants.COMPATIBLE_GROUP_TYPES[side_type] and \
            abs(start_idx - curr_idx) < len(TileSubsection.get_side_values()):
            return [subsection] +\
                   self._iterate_subsection_sides(
                       side_type, start_idx,
                       curr_idx + 1 if curr_idx > start_idx else curr_idx -1
                    )
        return []