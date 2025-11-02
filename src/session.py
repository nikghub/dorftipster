import ast
import copy
from typing import Dict, Tuple, List

import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot

from src.tile import Tile
from src.side import Side
from src.tile_subsection import TileSubsection
from src.side_type import SideType
from src.tile_evaluation import TileEvaluation
from src.tile_evaluation_factory import TileEvaluationFactory
from src.group import Group
from src.database_access import DatabaseAccess
from src.constants import DatabaseConstants

from src.tree import Tree


class Session(QObject):
    # UI signals
    dataframe_loaded = Signal(tuple)
    session_reset = Signal()
    session_updated = Signal(tuple)
    session_loaded = Signal()
    tile_placed = Signal(tuple)
    tile_undone = Signal(tuple)
    undone_tile_properties = Signal(tuple)
    candidate_tiles_computed = Signal(tuple)
    similar_tiles_seen = Signal(int)
    trigger_message_display = Signal(tuple)
    trigger_display_help = Signal()
    sessions_loaded_from_database = Signal(tuple)
    candidate_rotated = Signal(tuple)
    watched_coordinates_changed = Signal(tuple)
    coordinates_selected = Signal(tuple)

    def __init__(self, database_name=None, parent=None):
        super().__init__(parent)

        # (x, y) of tile : Tile
        self.played_tiles: Dict[Tuple[int, int], Tile] = {}

        # stores the sides of played tiles in all orientation as a tree
        # with the coordinates of the played tile at the leaf
        # this allows very fast lookup
        self.seen_tile_sides_tree = Tree()

        # group_id : Group
        self.groups: Dict[str, Group] = {}

        # (x, y) of tile that closed / connected group(s) : groups
        self.groups_marked_for_deletion_at_coords: Dict[
            Tuple[int, int], List[Group]
        ] = {}

        self.database = DatabaseAccess(database_name)

        # (x, y) : None - coordinates that allow placement for future tiles
        self.open_coords = {(0, 0): None}
        self.previous_open_tiles = None

        # (
        #    (x,y),
        #    Number of tiles that have been played that would perfectly match at the coordinates
        # )
        self.coordinate_watch_candidate = None

        # (x, y) :
        #   Number of tiles that have been played that would perfectly match at the coordinates
        # coordinates that are being watched by the user
        self.watched_open_coords = {}
        self.watched_coords_cache = None

        # score (without consideration of solved quests)
        self.score: int = 0

        # Database ID of the corresponding autosave session
        self.autosave_id = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.database.close_connection()

    @Slot()
    def handle_start_session(self):
        self.start()
        self.handle_tile_placed(self.played_tiles[(0, 0)])

    def start(self):
        self.reset()
        # first tile always all green
        first_tile = self.prepare_candidate(
            [SideType.GREEN], SideType.GREEN, coordinates=(0, 0)
        )
        self.place_candidate(first_tile)

    @Slot()
    def handle_reset_session(self):
        self.reset()
        self.session_reset.emit()

    def reset(self):
        self.played_tiles = {}
        self.seen_tile_sides_tree = Tree()
        self.groups = {}
        self.groups_marked_for_deletion_at_coords = {}
        self.open_coords = {(0, 0): None}
        self.previous_open_tiles = None
        self.coordinate_watch_candidate = None
        self.watched_open_coords = {}
        self.watched_coords_cache = None
        self.score = 0
        self.autosave_id = -1

    @Slot(tuple)
    def handle_watch(self, coordinates):
        if self.watch_coordinates(coordinates):
            self.update_coords_selection(coordinates)
            self.watched_coordinates_changed.emit(
                (self.watched_open_coords, coordinates, True)
            )

    def watch_coordinates(self, coordinates):
        if (
            coordinates in self.open_coords
            and coordinates not in self.watched_open_coords
        ):
            self.watched_open_coords[coordinates] = (
                self.get_num_played_tiles_matching_perfectly(coordinates)
            )
            return True
        return False

    @Slot(tuple)
    def handle_unwatch(self, coordinates):
        if self.unwatch_coordinates(coordinates):
            self.watched_coordinates_changed.emit(
                (self.watched_open_coords, coordinates, False)
            )
            self.update_coords_selection(coordinates)

    def unwatch_coordinates(self, coordinates):
        if coordinates in self.watched_open_coords:
            del self.watched_open_coords[coordinates]
            return True
        return False

    @Slot(tuple)
    def update_coords_selection(self, coordinates):
        self.select_coordinates(coordinates)
        self.coordinates_selected.emit(self.coordinate_watch_candidate)

    def select_coordinates(self, coordinates):
        # watch candidate should display same information as if it were watched
        self.coordinate_watch_candidate = None
        if (
            coordinates in self.open_coords
            and coordinates not in self.watched_open_coords
        ):
            self.coordinate_watch_candidate = (
                coordinates,
                self.get_num_played_tiles_matching_perfectly(coordinates),
            )

    @Slot(str)
    def handle_get_all_sessions_from_database(self, origin):
        try:
            sessions_df = self.get_all_sessions_from_database()
            self.sessions_loaded_from_database.emit((sessions_df, origin))
        except Exception as e:
            self.trigger_message_display.emit(
                ("Error", "Error loading sessions from database:\n" + str(e))
            )

    def get_all_sessions_from_database(self):
        return self.database.fetch_all_sessions()

    @Slot(int)
    def handle_delete_session_from_database(self, session_id):
        try:
            self.delete_from_database(session_id)
            self.trigger_message_display.emit(
                ("Success", "Session successfully deleted")
            )
        except Exception as e:
            self.trigger_message_display.emit(
                ("Error", f"Error deleting from database:\n{str(e)}")
            )

    def delete_from_database(self, session_id):
        self.database.delete_session_and_related(session_id)

    @Slot(str)
    def handle_save_session_to_database(self, session_name):
        try:
            self.save_to_database(session_name)
            self.trigger_message_display.emit(
                ("Success", f"Session {session_name} successfully saved")
            )
        except Exception as e:
            self.trigger_message_display.emit(
                ("Error", "Error saving to database:\n" + str(e))
            )

    def save_to_database(self, session_name):
        self.database.save_session(session_name, self)

    @Slot(str)
    def handle_save_session_to_csv(self, file_name):
        try:
            self.save_to_csv(file_name)
            self.trigger_message_display.emit(
                ("Success", f"Session successfully saved to {file_name}")
            )
        except Exception as e:
            self.trigger_message_display.emit(
                (
                    "Error",
                    "An error occured:\n" + str(e) + "\n" + "Could not save to ",
                    file_name,
                )
            )

    def save_to_csv(self, file_name):
        if file_name is None or not file_name:
            raise ValueError("No file name specified")

        list_of_tile_dicts = []
        # id,coordinates,side_type_seq,center_type,quest_type
        for i, tile in enumerate(self.played_tiles.values()):
            tile_dict = {}
            tile_dict["id"] = str(i)
            tile_dict["coordinates"] = str(tile.coordinates)
            tile_dict["side_type_seq"] = tile.get_side_type_seq()
            tile_dict["center_type"] = tile.get_center().type.to_character()
            tile_dict["quest_type"] = (
                tile.quest.type.to_character() if tile.quest is not None else ""
            )
            list_of_tile_dicts.append(tile_dict)

        data = pd.DataFrame(list_of_tile_dicts)
        data.to_csv(file_name, index=False)

    @Slot(tuple)
    def handle_load_session_from_database(self, args):
        try:
            session_id, load_simulated, load_tile_by_tile = args

            if load_tile_by_tile:
                # no autosave when using tile by tile as this is for debugging purposes only
                tile_data, watched_coords_data = self.database.load_session(session_id)
                self.dataframe_loaded.emit(tile_data)
            else:
                self.load_from_database(session_id, load_simulated)
                self.session_updated.emit(self)
                self.session_loaded.emit()
        except Exception as e:
            self.trigger_message_display.emit(
                ("Error", "Error loading from database:\n" + str(e))
            )

    def load_from_database(self, session_id, simulate_tile_placement):
        tile_data, watched_coords_data = self.database.load_session(session_id)
        if tile_data is None or tile_data.empty:
            raise ValueError(f"Error while reading session with id {session_id}")

        self.reset()
        self._load_tile_dataframe(tile_data, simulate_tile_placement)
        if not simulate_tile_placement:
            self._load_watched_coordinates_dataframe(watched_coords_data)

    @Slot(str)
    def handle_load_session_from_csv(self, file_name):
        try:
            self.load_from_csv(file_name, simulate_tile_placement=False)
            self.session_updated.emit(self)
            self.session_loaded.emit()
        except Exception as e:
            self.trigger_message_display.emit(
                (
                    "Error",
                    "An error occured:\n" + str(e) + "\n" + "Could not load ",
                    file_name,
                )
            )

    def load_from_csv(self, file_name, simulate_tile_placement):
        if file_name is None or not file_name:
            raise ValueError("No file name specified")

        data = pd.read_csv(file_name)
        if data is None or data.empty:
            raise ValueError(f"File {file_name} is empty or could not be read")
        data.set_index("id", inplace=True)

        self.reset()
        self._load_tile_dataframe(data, simulate_tile_placement)

    @Slot(tuple)
    def handle_compute_candidates(self, args):
        side_types, center_type, quest_type = args

        # consider single char sequence for ease of use
        if len(side_types) == 1:
            center_type = side_types

        if not quest_type:
            quest_type = None

        candidates = self.compute_candidate_tiles(side_types, center_type, quest_type)
        if len(candidates) == 0:
            self.trigger_display_help.emit()
            return

        rated_candidates = self.compute_tile_ratings(candidates)
        best_candidate_per_coords = {}
        for idx, candidate in enumerate(rated_candidates):
            # candidate list is ordered by rating,
            # therefore the first candidate we encounter has the highest rating
            if candidate.tile.coordinates in best_candidate_per_coords:
                continue
            best_candidate_per_coords[candidate.tile.coordinates] = (idx, candidate)

        self.candidate_tiles_computed.emit(
            (rated_candidates, best_candidate_per_coords, self.open_coords)
        )

        self.similar_tiles_seen.emit(
            len(
                self.seen_tile_sides_tree.find_matching_tiles(
                    [candidates[0].get_side(s).type for s in TileSubsection.get_side_values()]
                )
            )
        )

    def compute_candidate_tiles(self, side_type_seq, center_type, quest_type=None):
        if not Tile.is_valid_side_sequence(side_type_seq) or not SideType.is_valid(
            center_type
        ):
            return []

        # first tile placed (e.g. when loading from database/csv)
        # -> candidate tile is the tile itself
        if len(self.played_tiles) == 0:
            return [self.prepare_candidate(side_type_seq, center_type, (0, 0))]

        # iterate over all open tiles and create candidate tiles by adding all possible orientations
        candidates = []
        for coords in self.open_coords.keys():
            open_tile = Tile(
                side_types=side_type_seq, coordinates=coords, center_type=center_type
            )
            for candidate in open_tile.create_all_orientations(include_self=True):
                self._enrich_tile(candidate, quest_type)
                if candidate.get_placement() != Tile.Placement.NOT_POSSIBLE:
                    candidates.append(candidate)

        return candidates

    def _update_open_tiles(self, tile):
        if not self.open_coords or tile.coordinates not in self.open_coords:
            return

        del self.open_coords[tile.coordinates]
        for s in TileSubsection.get_side_values():
            if (
                neighbor_coords := tile.get_neighbor_coords(s)
            ) not in self.played_tiles:
                self.open_coords[neighbor_coords] = None

    def compute_open_coords_for_tile(self, tile):
        if not self.open_coords or not tile or tile.coordinates not in self.open_coords:
            return {}

        open_coords_copy = copy.copy(self.open_coords)
        del open_coords_copy[tile.coordinates]
        for s in TileSubsection.get_side_values():
            if (
                neighbor_coords := tile.get_neighbor_coords(s)
            ) not in self.played_tiles:
                open_coords_copy[neighbor_coords] = None

        return open_coords_copy

    def prepare_candidate(self, side_types, center_type, coordinates, quest_type=None):
        candidate = Tile(
            side_types=side_types, center_type=center_type, coordinates=coordinates
        )
        self._enrich_tile(candidate, quest_type)
        if candidate.get_placement() == Tile.Placement.NOT_POSSIBLE:
            return None

        return candidate

    def compute_tile_ratings(self, candidate_tiles):
        tile_evaluation = TileEvaluationFactory.create(candidate_tiles, self)

        return tile_evaluation.get_rated_tiles()

    def get_open_count(self):
        return sum(
            [
                1 if tile.get_num_sides(Side.Placement.UNKNOWN_MATCH) != 0 else 0
                for tile in self.played_tiles.values()
            ]
        )

    def get_closed_count(self):
        return sum(
            [
                1 if tile.get_num_sides(Side.Placement.UNKNOWN_MATCH) == 0 else 0
                for tile in self.played_tiles.values()
            ]
        )

    def get_perfect_placement_count(self):
        return sum(
            [
                1 if tile.get_num_sides(Side.Placement.PERFECT_MATCH) == 6 else 0
                for tile in self.played_tiles.values()
            ]
        )

    def get_imperfect_placement_count(self):
        return self.get_closed_count() - self.get_perfect_placement_count()

    def get_open_placement_count(self, tile_placement):
        return sum(
            [
                (
                    1
                    if tile.get_num_sides(Side.Placement.UNKNOWN_MATCH) != 0
                    and tile.get_placement() == tile_placement
                    else 0
                )
                for tile in self.played_tiles.values()
            ]
        )

    def get_perfect_placement_percentage(self):
        total_closed = self.get_closed_count()
        if total_closed == 0:
            return 0
        return round((self.get_perfect_placement_count() / total_closed) * 100, 2)

    def autosave(self, tile: Tile, undo_tile_placement: bool = False):
        if self.autosave_id >= 0:
            if undo_tile_placement:
                self.database.remove_last_placed_tile(self.autosave_id)
            else:
                self.database.add_placed_tile(self.autosave_id, tile)
        else:
            autosave_ids = self.database.find_session_ids_by_name(
                DatabaseConstants.AUTOSAVE_NAME
            )
            if len(autosave_ids) > 0:
                # reuse same autosave for all games
                self.autosave_id = autosave_ids[0]
                self.database.delete_session_and_related(
                    self.autosave_id, leave_empty_session=True
                )
                self.database.fill_session_tiles(self.autosave_id, self.played_tiles)
            else:
                self.autosave_id = self.database.save_session(
                    DatabaseConstants.AUTOSAVE_NAME,
                    self,
                    save_watched_coordinates=False,
                )

    @Slot(tuple)
    def handle_place_candidate(self, tile):
        if tile is not None:
            self.place_candidate(tile)
            try:
                self.autosave(tile)
            except Exception as e:
                print(f"ERROR: Autosaving session was not successful: {e}")
            self.handle_tile_placed(tile)

    @Slot(tuple)
    def handle_tile_placed(self, tile):
        self.session_updated.emit(self)
        self.tile_placed.emit(tile)

    def place_candidate(self, tile: Tile, quest_type=None):
        if tile is None:
            raise ValueError("Candidate is not valid")
        if tile.coordinates in self.played_tiles:
            raise ValueError(
                "Candidate coordinates invalid. There is already a tile at that position"
            )

        self._update_tile_neighbor_placements(tile)
        self.played_tiles[tile.coordinates] = tile
        self._update_groups(tile)
        self._update_score(tile)
        self._update_seen_tiles(tile)
        self._update_watched_coordinates()

        self.previous_open_tiles = copy.copy(self.open_coords)
        self._update_open_tiles(tile)

    @Slot()
    def handle_undo_last_tile(self):
        if len(self.played_tiles) > 1:
            undone_tile = self.undo_last_tile()
            try:
                self.autosave(undone_tile, undo_tile_placement=True)
            except Exception as e:
                print(f"ERROR: Autosaving session was not successful: {e}")

            self.session_updated.emit(self)
            self.tile_undone.emit(undone_tile)
            auto_compute = False
            auto_place = False
            self.undone_tile_properties.emit(
                (
                    undone_tile.get_side_type_seq(),
                    undone_tile.get_center().type.to_character(),
                    auto_compute,
                    auto_place,
                )
            )

    def undo_last_tile(self):
        coordinates, tile = self.played_tiles.popitem()
        self._update_tile_neighbor_placements(tile, undo_tile_placement=True)
        self._update_groups(tile, undo_tile_placement=True)
        self._update_score(tile, undo_tile_placement=True)
        self._update_seen_tiles(tile, undo_tile_placement=True)
        self._update_watched_coordinates(undo_tile_placement=True)

        self.open_coords = self.previous_open_tiles
        self.previous_open_tiles = None

        return tile

    @Slot(tuple)
    def handle_rotate_candidate(self, args):
        candidate, offset = args

        rotation = self.get_rotated_candidate(candidate.tile, offset)

        if rotation is not None:
            self.candidate_rotated.emit(rotation)

    def get_rotated_candidate(self, candidate: Tile, offset: int):
        valid_rotations = []

        if offset not in [-1, 1]:
            return None

        rotations = candidate.get_rotations()
        # same sided hexagon or error
        if len(rotations) in [0, 1]:
            return None

        for rotation in rotations:
            self._enrich_tile(rotation)
            if rotation.get_placement() != Tile.Placement.NOT_POSSIBLE:
                valid_rotations.append(rotation)

        # rotating not allowed as placement not possible for all rotations
        if len(valid_rotations) == 0:
            return None

        if offset == -1:  # previous
            return valid_rotations[-1]
        # next
        return valid_rotations[0]

    def get_num_played_tiles_matching_perfectly(self, open_coords):
        # computes the number of tiles that have already been played that would
        # match all known sides of the open position
        open_coords_side_types = []
        for subsection in TileSubsection.get_side_values():
            neighbor_coords = Tile.get_coordinates(open_coords, subsection)
            if neighbor_coords not in self.played_tiles:
                open_coords_side_types.append(SideType.UNKNOWN)
            else:
                open_coords_side_types.append(
                    self.played_tiles[neighbor_coords]
                        .get_side(Tile.get_opposing(subsection))
                        .type
                )

        return len(
            self.seen_tile_sides_tree.find_matching_tiles(open_coords_side_types)
        )

    def _update_score(self, tile: Tile, undo_tile_placement: bool = False):
        tile_score = 60 * tile.get_num_perfectly_closed(self.played_tiles) + \
                     10 * tile.get_num_sides(Side.Placement.PERFECT_MATCH)

        self.score += -tile_score if undo_tile_placement else tile_score

    def _update_seen_tiles(self, tile: Tile, undo_tile_placement: bool = False):
        if undo_tile_placement:
            self.seen_tile_sides_tree.remove_tile(tile)
        else:
            self.seen_tile_sides_tree.add_tile(tile)

    def _update_watched_coordinates(self, undo_tile_placement: bool = False):
        if not undo_tile_placement:
            self.watched_coords_cache = None

        for coords in self.watched_open_coords.keys():
            # update the amount of seen tiles that would perfectly match
            self.watched_open_coords[coords] = (
                self.get_num_played_tiles_matching_perfectly(coords)
            )

            if not undo_tile_placement:
                # if a watched coordinate now contains a tile, cache it
                # as we might need to restore it in the undo case.
                if coords in self.played_tiles:
                    self.watched_coords_cache = coords

        if self.watched_coords_cache is not None:
            if not undo_tile_placement:
                # remove from the watched coordinates list
                del self.watched_open_coords[self.watched_coords_cache]
                self.watched_coordinates_changed.emit(
                    (self.watched_open_coords, self.watched_coords_cache, False)
                )
            else:
                # restore watch status
                self.watched_open_coords[self.watched_coords_cache] = (
                    self.get_num_played_tiles_matching_perfectly(
                        self.watched_coords_cache
                    )
                )
                self.watched_coordinates_changed.emit(
                    (self.watched_open_coords, self.watched_coords_cache, True)
                )
                self.watched_coords_cache = None

    def _load_tile_dataframe(self, dataframe, simulate_tile_placement):
        self.played_tiles = {}
        self.seen_tile_sides_tree = Tree()
        self.groups = {}

        for index, row in dataframe.iterrows():
            tile = None
            # when simulating, do not consider coordinates, where tiles have been place but
            # instead compute best candidate and always just place that at the suggested coordinates
            if simulate_tile_placement:
                candidates = self.compute_candidate_tiles(
                    row["side_type_seq"],
                    row["center_type"],
                    None if pd.isna(row["quest_type"]) else row["quest_type"],
                )
                if candidates is not None and candidates:
                    rated_candidates = self.compute_tile_ratings(candidates)
                    tile = rated_candidates[0].tile
                    self.place_candidate(tile)

            else:
                tile = self.prepare_candidate(
                    row["side_type_seq"],
                    row["center_type"],
                    ast.literal_eval(row["coordinates"]),
                )

                self.place_candidate(
                    tile, None if pd.isna(row["quest_type"]) else row["quest_type"]
                )

    def _load_watched_coordinates_dataframe(self, dataframe):
        if dataframe is None or dataframe.empty:
            return

        for index, row in dataframe.iterrows():
            self.watch_coordinates(ast.literal_eval(row["coordinates"]))

    def _update_groups(self, tile: Tile, undo_tile_placement: bool = False):
        def mark_group_for_deletion(group_id):
            if group_id in [
                g.id
                for groups in self.groups_marked_for_deletion_at_coords.values()
                for g in groups
            ]:
                return

            if tile.coordinates not in self.groups_marked_for_deletion_at_coords:
                self.groups_marked_for_deletion_at_coords[tile.coordinates] = []

            self.groups_marked_for_deletion_at_coords[tile.coordinates].append(
                self.groups[group_id]
            )

        if undo_tile_placement:
            # remove new groups
            ids_to_delete = []
            for group_id, group in self.groups.items():
                if group.start_tile.coordinates == tile.coordinates:
                    ids_to_delete.append(group_id)
            for group_id in ids_to_delete:
                del self.groups[group_id]

            # add groups again that were marked for deletion by the undone tile
            if tile.coordinates in self.groups_marked_for_deletion_at_coords:
                for group in self.groups_marked_for_deletion_at_coords[
                    tile.coordinates
                ]:
                    self.groups[group.id] = group
                del self.groups_marked_for_deletion_at_coords[tile.coordinates]

        else:
            for group_id, group_participation in tile.group_participation.items():
                # transfer all new groups
                if group_id not in self.groups:
                    self.groups[group_id] = group_participation.group

                # mark all groups that have been merged with other for deletion
                for consumed_group_id in group_participation.group.consumed_groups:
                    if consumed_group_id in self.groups:
                        mark_group_for_deletion(consumed_group_id)

        # recompute groups to ensure consistency
        for group in self.groups.values():
            group.compute(self.played_tiles)

            # mark groups for deletion that are closed by the placed tile
            if len(group.possible_extensions) == 0:
                mark_group_for_deletion(group.id)

        final_deletion = []
        for coordinates, groups in self.groups_marked_for_deletion_at_coords.items():
            # delete all groups that have been marked
            for group in groups:
                if group.id in self.groups:
                    del self.groups[group.id]

            # final deletion may only be done once the next tile has been placed,
            # as the last played tile may still be undone
            if tile.coordinates != coordinates:
                final_deletion.append(coordinates)

        for coordinates in final_deletion:
            del self.groups_marked_for_deletion_at_coords[coordinates]

    def _update_tile_side_placements(self, tile):
        for subsection in TileSubsection.get_side_values():
            side = tile.get_side(subsection)
            opposing_side = self._get_tile_side(
                tile.get_neighbor_coords(subsection), Tile.get_opposing(subsection)
            )
            if opposing_side is not None:
                side.placement = TileEvaluation.compute_side_placement_match(
                    side.type, opposing_side.type
                )

    def _update_tile_neighbor_placements(self, tile, undo_tile_placement=False):
        for subsection in TileSubsection.get_side_values():
            side = tile.get_side(subsection)
            opposing_side = self._get_tile_side(
                tile.get_neighbor_coords(subsection), Tile.get_opposing(subsection)
            )
            if opposing_side is not None:
                if undo_tile_placement:  # tile will be removed due to undo
                    # reset to unknown to ensure the undone tile's coordinate is considered again
                    opposing_side.placement = Side.Placement.UNKNOWN_MATCH
                else:
                    opposing_side.placement = (
                        TileEvaluation.compute_side_placement_match(
                            opposing_side.type, side.type
                        )
                    )

    def _get_tile_side(self, coordinates, subsection):
        if coordinates in self.played_tiles:
            return self.played_tiles[coordinates].get_side(subsection)

        return None

    def _update_group_participation(self, tile):
        Group.update_group_participation(self.groups, self.played_tiles, tile)

    def _enrich_tile(self, tile, quest_type=None):
        self._update_tile_side_placements(tile)
        self._update_group_participation(tile)

        # TODO possibly make use of quest type
