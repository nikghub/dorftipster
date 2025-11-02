from src.tree import Tree, TreeNode
from src.tile import Tile
from src.side_type import SideType
from src.tile_subsection import TileSubsection

def test_tree_init():
    tree = Tree()

    assert tree.root is not None
    assert len(tree.root.children) == 0
    assert len(tree.root.coordinates) == 0

def test_tree_node_eq():
    tree_node1 = TreeNode()
    tree_node2 = TreeNode()

    assert tree_node1 == tree_node2

    assert tree_node1 != SideType.GREEN
    assert tree_node1 != "some string"

def test_tree_eq():
    tree1 = Tree()
    tree2 = Tree()
    assert tree1 == tree2

    # different type
    assert tree1 != SideType.GREEN
    assert tree1 != "some string"

    tile0 = Tile([SideType.GREEN], SideType.GREEN, (0,0))
    tile1 = Tile([SideType.GREEN], SideType.GREEN, (0,0))
    tile2 = Tile([SideType.GREEN], SideType.GREEN, (0,4))
    tile3 = Tile([SideType.GREEN, SideType.WOODS, SideType.CROPS, SideType.HOUSE, SideType.WOODS, SideType.HOUSE], SideType.HOUSE, (0,0))

    tree1.add_tile(tile0)
    tree2.add_tile(tile1)
    assert tree1 == tree2

    tree1.remove_tile(tile0)
    tree2.remove_tile(tile1)
    assert tree1 == tree2

    tree1.add_tile(tile1)
    tree2.add_tile(tile2)
    assert tree1 != tree2

    tree1.remove_tile(tile1)
    tree2.remove_tile(tile2)
    assert tree1 == tree2

    tree1.add_tile(tile1)
    tree2.add_tile(tile3)
    assert tree1 != tree2


def test_add_tile():
    tree = Tree()

    types = [
        SideType.GREEN,
        SideType.WOODS,
        SideType.CROPS,
        SideType.HOUSE
    ]

    tile = Tile([types[0], types[1], types[2], types[3], types[0], types[1]], types[2], (0,0))

    tree.add_tile(tile)

    assert len(tree.root.children) == len(types)
    for type in types:
        assert type in tree.root.children

    for orientation in tile.create_all_orientations():
        found_tiles = tree.find_matching_tiles([orientation.get_side(s).type for s in TileSubsection.get_side_values()])
        assert len(found_tiles) == 1

    tree.remove_tile(tile)
    # ensure that empty nodes get removed again
    assert len(tree.root.children) == 0

def test_error_cases():
    tree = Tree()

    assert not tree.find_matching_tiles("some gargabe")
    for i in range(6+1):
        if i == 6:
            # valid input but empty tree
            assert not tree.find_matching_tiles([SideType.CROPS]*i)
        else:
            # invalid input
            assert not tree.find_matching_tiles([SideType.CROPS]*i)
