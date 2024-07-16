import uuid
from typing import List, Dict, Tuple

from src.side_type import SideType
from src.tile_subsection import TileSubsection
from src.tile import Tile

class Group:
    # compatibility of a type with group types
    COMPATIBLE_GROUP_TYPES = {
        SideType.CROPS : [SideType.CROPS],
        SideType.HOUSE : [SideType.HOUSE],
        SideType.RIVER : [SideType.RIVER, SideType.PONDS, SideType.STATION],
        SideType.PONDS : [SideType.PONDS, SideType.RIVER, SideType.STATION],
        SideType.TRAIN : [SideType.TRAIN, SideType.STATION],
        SideType.STATION : [SideType.STATION, SideType.RIVER, SideType.TRAIN, SideType.PONDS],
        SideType.WOODS : [SideType.WOODS]
        }
    # types that allow a group creation
    ALLOWED_GROUP_TYPES = [
        SideType.CROPS,
        SideType.HOUSE,
        SideType.RIVER,
        SideType.PONDS,
        SideType.TRAIN,
        SideType.WOODS
    ]

    def __init__(self, start_tile: Tile, side_type: SideType,
                 subsections: List[TileSubsection], group_id=None):
        self.start_tile: Tile = start_tile
        self.start_tile_subsections: List[TileSubsection] = subsections
        self.type: SideType = side_type
        self.tile_coordinates: List[Tuple[int, int]] = [start_tile.coordinates]
        self.size: int = len(subsections)
        self.possible_extensions: Dict[Tuple[int, int] : List[TileSubsection]] = \
            {start_tile.neighbor_coordinates[s] : [opp_s]\
            for s, opp_s in Tile.get_opposite_dict().items() if opp_s is not None}
        if group_id is not None:
            self.id = group_id
        else:
            self.id: str = str(uuid.uuid4()).replace('-', '')[:8]  # generate random uuid

        # contains ids of groups that have been consumed and therefore merged into this group
        self.consumed_groups: List[str] = []

    def __eq__(self, other):
        if not isinstance(other, Group):
            return False

        return self.type in Group.COMPATIBLE_GROUP_TYPES[other.type] and\
               sorted(self.tile_coordinates) == sorted(other.tile_coordinates) and\
               self.size == other.size and\
               sorted(self.possible_extensions.keys()) == sorted(other.possible_extensions.keys())

    def __lt__(self, other):
        return self.start_tile.coordinates < other.start_tile.coordinates

    @classmethod
    def is_type_restricted(cls, side_type):
        return side_type in [SideType.RIVER, SideType.PONDS, SideType.TRAIN, SideType.STATION]

    @classmethod
    def update_group_participation(cls, groups, played_tiles, tile):
        # extend an existing group or create a new group for all connect subsections of the tile
        for side_type, subsections in Group.get_connected_subsection_groups(tile):
            extends_existing_group = False
            for group in groups.values():
                if Group._extend_group(group, played_tiles, tile, subsections):
                    extends_existing_group = True

            if not extends_existing_group and side_type in Group.ALLOWED_GROUP_TYPES:
                # create new group for the subsections that are not adding to any existing groups
                new_group = Group(tile, side_type, subsections)
                new_group.compute(played_tiles)

        # possibly merge groups that have been connected through the given tile
        groups = [gp.group for gp in tile.group_participation.values()]
        index_groups = []  # This will hold lists of indices grouped by equality of the groups
        for i, group in enumerate(groups):
            found_group = False
            for index_group in index_groups:
                if groups[index_group[0]] == group:
                    index_group.append(i)
                    found_group = True
                    break
            if not found_group:
                index_groups.append([i])

        for index_group in index_groups:
            # delete equal groups, only keep first
            for i in index_group[1:]:
                del tile.group_participation[groups[i].id]
                # keep track of the consumed group
                # in order to also delete them from the session later
                remaining_group_id = groups[index_group[0]].id
                tile.group_participation[remaining_group_id]\
                    .group.consumed_groups.append(groups[i].id)

        # update the possible extensions to ensure that the given tile is removed
        for gp in tile.group_participation.values():
            if tile.coordinates in gp.group.tile_coordinates and \
            tile.coordinates in gp.group.possible_extensions:
                del gp.group.possible_extensions[tile.coordinates]

    def compute(self, played_tiles):
        # reset as we are recomputing
        self.tile_coordinates = []
        self.possible_extensions = {}
        self.size = 0

        # the group size will be the count of all tiles sides + tile centers that are connected
        # -> start from the start tile and allow to recurse into all directions
        self.compute_from_tile(played_tiles, self.start_tile, self.start_tile_subsections)

    def get_group_connected_tile_subsections(self, tile, origin_subsection):
        """
        Returns the subsections of the given tile that are connected to the group
        through the side of the tile at the origin_subsection.

        Args:
            tile: The tile to analyze
            origin_subsection: The subsection of the side that connects to the group

        Returns:
            List of subsections for the given tile that are connected to the group,
            including the origin_subsection
        """
        if tile.subsections[origin_subsection].type not in self.COMPATIBLE_GROUP_TYPES[self.type]:
            # incompatible type at origin, therefore no connection to the group
            return []

        if tile.subsections[origin_subsection].isolated:
            # if the tile that connects to the group is isolated, only that tile is returned
            return [origin_subsection]

        if tile.get_center().type in self.COMPATIBLE_GROUP_TYPES[self.type]:
            # we may reach all sides of the tile through the center,
            # therefore return all subsections where the side type matches the group type
            # and the side is not marked as isolated
            return [s for s in TileSubsection.get_all_values()
                    if tile.subsections[s].type in self.COMPATIBLE_GROUP_TYPES[self.type] and
                       not tile.subsections[s].isolated]

        start_idx = TileSubsection.get_index(origin_subsection)

        # iterate clockwise and counter clockwise
        # to collect connected subsections of sides where the type matches
        return list(set(
            [origin_subsection] + \
            self._iterate_subsection_sides(tile, self.type, start_idx, start_idx+1) + \
            self._iterate_subsection_sides(tile, self.type, start_idx, start_idx-1)
            ))

    @classmethod
    def get_connected_subsection_groups(cls, tile):
        """
        Returns all of the subsection groups for the tile. That is:
        All subsections that are connected and have a type that is compatible with groups.

        Args:
            tile: The tile to analyze

        Returns:
            A list of pairs, where each pair consists of
            the shared type and the corresponding subsections.
        """
        subsection_groups = []
        if tile.get_center().type in cls.COMPATIBLE_GROUP_TYPES:
            # we may reach all sides of the tile through the center,
            # therefore return all subsections where the side type matches the center type
            # andthe side is not marked as isolated
            center_group = [s for s in TileSubsection.get_all_values()
                            if tile.subsections[s].type == tile.get_center().type and
                               not tile.subsections[s].isolated]
            # only add center group if at least one side is involved,
            # otherwise the group can't ever be extended
            if len(center_group) > 1:
                subsection_groups.append((tile.get_center().type, center_group))
            remaining_subsections =\
                [s for s in TileSubsection.get_side_values() if s not in center_group]
        else:
            remaining_subsections = TileSubsection.get_side_values()

        while len(remaining_subsections) > 0:
            start_subsection = remaining_subsections[0]
            start_idx = TileSubsection.get_index(start_subsection)
            side_type = tile.subsections[start_subsection].type
            if side_type not in cls.COMPATIBLE_GROUP_TYPES:
                del remaining_subsections[0]
                continue

            # iterate clockwise and counter clockwise
            # to collect connected subsections of sides where the type matches
            subsections = list(set(
                [start_subsection] + \
                cls._iterate_subsection_sides(tile, side_type, start_idx, start_idx+1) + \
                cls._iterate_subsection_sides(tile, side_type, start_idx, start_idx-1)
                ))
            subsection_groups.append((side_type, subsections))

            remaining_subsections = [s for s in remaining_subsections if s not in subsections]

        return subsection_groups

    @classmethod
    def _iterate_subsection_sides(cls, tile, side_type, start_idx, curr_idx):
        subsection = TileSubsection.at_index(curr_idx)
        if tile.subsections[subsection].type in Group.COMPATIBLE_GROUP_TYPES[side_type] and \
            abs(start_idx - curr_idx) < len(TileSubsection.get_side_values()):
            return [subsection] +\
                   cls._iterate_subsection_sides(
                       tile, side_type, start_idx,
                       curr_idx + 1 if curr_idx > start_idx else curr_idx -1
                    )
        return []

    @classmethod
    def _extend_group(cls, group, played_tiles, tile, subsections):
        if not group.is_extended_by_tile_subsections(tile, subsections):
            return False

        # we might encounter the same group multiple times
        # as we might connect from different subsections
        if group.id in tile.group_participation:
            tile.group_participation[group.id].group.compute_from_tile(played_tiles,
                                                                       tile, subsections)
        else:
            # create a copy and extend the copy
            group_copy = Group(group.start_tile, group.type, group.start_tile_subsections, group.id)
            group_copy.compute(played_tiles)
            group_copy.compute_from_tile(played_tiles, tile, subsections)

        return True

    def is_extended_by_tile_subsections(self, new_tile, subsections):
        if new_tile.coordinates not in self.possible_extensions:
            return False

        for subsection in subsections:
            if subsection in self.possible_extensions[new_tile.coordinates] and \
               new_tile.subsections[subsection].type in self.COMPATIBLE_GROUP_TYPES[self.type]:
                return True

        return False

    def compute_from_tile(self, played_tiles, tile, subsections, origin_subsection=None):
        # count of connected subsections that the tile itself contributes to the groups overall size
        tile_group_size_contribution = 0

        if tile.coordinates not in self.tile_coordinates:
            self.tile_coordinates.append(tile.coordinates)
            # recompute tile group participation: keep track of subsections of the tile
            # that have been seen already to avoid infinite recursion
            tile.group_participation[self.id] = Tile.GroupParticipation(self, subsections=[])

        for subsection in subsections:
            if subsection in tile.group_participation[self.id].subsections:
                continue

            # count the side
            tile.group_participation[self.id].subsections.append(subsection)
            tile_group_size_contribution += 1

            # do not transition back to where we came from
            if subsection == origin_subsection:
                continue

            # see if a tile is played at the opposing side of the current tile
            opposing_subsection = Tile.get_opposing(subsection)
            if opposing_subsection is None:
                continue

            opposing_tile_coords = tile.neighbor_coordinates[subsection]

            # collect possible extension points for the group
            if opposing_tile_coords not in played_tiles:
                if opposing_tile_coords not in self.possible_extensions:
                    self.possible_extensions[opposing_tile_coords] = []

                self.possible_extensions[opposing_tile_coords].append(opposing_subsection)
                continue

            opposing_tile = played_tiles[opposing_tile_coords]

            if opposing_tile.subsections[opposing_subsection].type not in \
                   self.COMPATIBLE_GROUP_TYPES[self.type]:
                # opposing side is of an incompatible type -> no further expansion
                continue

            # recursive call to compute the neighboring tile contribution to the group size
            self.compute_from_tile(played_tiles,
                                    opposing_tile,
                                    self.get_group_connected_tile_subsections(opposing_tile,
                                                                              opposing_subsection),
                                    opposing_subsection)

        self.size += tile_group_size_contribution
