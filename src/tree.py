from typing import List

from src.tile import Tile
from src.tile_evaluation import TileEvaluation
from src.tile_subsection import TileSubsection
from src.side_type import SideType

class TreeNode:
    def __init__(self):
        self.children = {}
        self.coordinates = {}

    def __eq__(self, other):
        if isinstance(other, TreeNode):
            return self.children == other.children and \
                   self.coordinates == other.coordinates
        return False

class Tree:
    def __init__(self):
        self.root = TreeNode()

    def __eq__(self, other):
        if isinstance(other, Tree):
            return self.root == other.root
        return False

    def add_tile(self, tile: Tile):
        for orientation in tile.create_all_orientations():
            current_node = self.root
            for s in TileSubsection.get_side_values():
                side = orientation.get_side(s)
                if side.type not in current_node.children:
                    current_node.children[side.type] = TreeNode()
                current_node = current_node.children[side.type]

            current_node.coordinates[tile.coordinates] = None

    def remove_tile(self, tile: Tile):
        for orientation in tile.create_all_orientations():
            current_node = self.root
            path = []

            for s in TileSubsection.get_side_values():
                side = orientation.get_side(s)
                if side.type not in current_node.children:
                    return
                child = current_node.children[side.type]
                path.append((current_node, side.type))
                current_node = child

            if tile.coordinates in current_node.coordinates:
                del current_node.coordinates[tile.coordinates]

            # Clean up the tree
            for parent, child_side_type in reversed(path):
                child = parent.children[child_side_type]
                if not child.coordinates and not child.children:
                    del parent.children[child_side_type]

    def find_matching_tiles(self, side_types: List[SideType]) -> List[Tile]:
        matching_tile_coordinates = {}

        if not isinstance(side_types, list) or len(side_types) != 6:
            return []

        def traverse(node: TreeNode, depth: int):
            if depth == len(side_types):
                matching_tile_coordinates.update(node.coordinates)
                return

            side_type = side_types[depth]
            if side_type == SideType.UNKNOWN:
                for any_side_type in SideType.get_values():
                    if any_side_type in node.children:
                        traverse(node.children[any_side_type], depth + 1)
            else:
                for compatible_side_type in TileEvaluation.PERFECT_MATCH_DICT[side_type]:
                    if compatible_side_type in node.children:
                        traverse(node.children[compatible_side_type], depth + 1)

        traverse(self.root, 0)
        return matching_tile_coordinates
