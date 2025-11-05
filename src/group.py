import uuid
from typing import List, Dict, Tuple

from src.side_type import SideType
from src.tile_subsection import TileSubsection
from src.tile import Tile
from src.constants import Constants

class Group:

    def __init__(self, start_tile: Tile, side_type: SideType,
                 subsections: List[TileSubsection], group_id=None):
        self.start_tile: Tile = start_tile
        self.start_tile_subsections: List[TileSubsection] = subsections
        self.type: SideType = side_type
        self.tile_coordinates: set[Tuple[int, int]] = {start_tile.coordinates}
        self.size: int = len(subsections)
        self.possible_extensions: Dict[Tuple[int, int] : List[TileSubsection]] = \
            {start_tile.get_neighbor_coords(s) : [Tile.get_opposing(s)]\
            for s in TileSubsection.get_side_values()}
        if group_id is not None:
            self.id = group_id
        else:
            self.id: str = str(uuid.uuid4()).replace('-', '')[:8]  # generate random uuid

        # contains ids of groups that have been consumed and therefore merged into this group
        self.consumed_groups: List[str] = []

    def __eq__(self, other):
        if not isinstance(other, Group):
            return False

        return self.type in Constants.COMPATIBLE_GROUP_TYPES[other.type] and\
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
        for side_type, subsections in tile.get_connected_subsection_groups():
            extends_existing_group = False
            for group in groups.values():
                if Group._extend_group(group, played_tiles, tile, subsections):
                    extends_existing_group = True

            if not extends_existing_group and side_type in Constants.ALLOWED_GROUP_TYPES:
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
        self.tile_coordinates.clear()
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
        origin_side = tile.get_side(origin_subsection)
        compatible_types = Constants.COMPATIBLE_GROUP_TYPES[self.type]
        if origin_side.type not in compatible_types:
            # incompatible type at origin, therefore no connection to the group
            return []

        if origin_side.isolated:
            # if the tile that connects to the group is isolated, only that tile is returned
            return [origin_subsection]

        connected_subsection_groups = tile.get_connected_subsection_groups()
        for group_type, connected_subsections in connected_subsection_groups:
            if group_type in compatible_types and origin_subsection in connected_subsections:
                return connected_subsections

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
               new_tile.get_side(subsection).type in Constants.COMPATIBLE_GROUP_TYPES[self.type]:
                return True

        return False

    def compute_from_tile(self, played_tiles, tile, subsections, origin_subsection=None):
        # count of connected subsections that the tile itself contributes to the groups overall size
        tile_group_size_contribution = 0

        if tile.coordinates not in self.tile_coordinates:
            self.tile_coordinates.add(tile.coordinates)
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

            opposing_tile_coords = tile.get_neighbor_coords(subsection)

            # collect possible extension points for the group
            if opposing_tile_coords not in played_tiles:
                if opposing_tile_coords not in self.possible_extensions:
                    self.possible_extensions[opposing_tile_coords] = []

                self.possible_extensions[opposing_tile_coords].append(opposing_subsection)
                continue

            opposing_tile = played_tiles[opposing_tile_coords]

            if opposing_tile.get_side(opposing_subsection).type not in \
                   Constants.COMPATIBLE_GROUP_TYPES[self.type]:
                # opposing side is of an incompatible type -> no further expansion
                continue

            # recursive call to compute the neighboring tile contribution to the group size
            self.compute_from_tile(played_tiles,
                                    opposing_tile,
                                    self.get_group_connected_tile_subsections(opposing_tile,
                                                                              opposing_subsection),
                                    opposing_subsection)

        self.size += tile_group_size_contribution
