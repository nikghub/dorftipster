from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QApplication
from PySide6.QtCore import Qt, Slot, Signal, QPointF, QEvent
from PySide6.QtGui import QPainter, QKeySequence, QBrush, QMouseEvent, QKeyEvent

from src.ui.constants import UIConstants
from src.tile_subsection import TileSubsection
from src.tile import Tile

from src.ui.placement_rated_tile_item import PlacementRatedTileItem
from src.ui.landscape_tile_item import LandscapeTileItem
from src.ui.candidate_tile_item import CandidateTileItem
from src.ui.open_coordinate_item import OpenCoordinateItem
from src.ui.utils import to_scene_coordinates, get_candidate_rating_color


class TileMapView(QGraphicsView):
    candidate_selected = Signal(int)
    coordinates_selected = Signal(tuple)
    confirm_selected_candidate = Signal()
    trigger_rotation = Signal(tuple)
    trigger_watch_coordinates = Signal(tuple)
    trigger_unwatch_coordinates = Signal(tuple)
    trigger_toggle_open_coords_display = Signal()
    trigger_clear_coordinates_selection = Signal()
    trigger_toggle_map_display = Signal()

    def __init__(self, layer_selection=None):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(UIConstants.BACKGROUND_COLOR))

        self.layer_selection = layer_selection
        self.initial_center = self.mapToScene(self.viewport().rect().center())

        self.candidates = []
        self.selected_candidate = None
        self.best_candidates = {}
        self.played_tiles = {}
        self.open_coords_list = []
        self.selected_open_coords = None
        self.watched_open_coords_list = {}
        self.open_coordinates_enabled = False
        self.open_coordinates_auto_toggled = False
        self._mouse_moved = False
        self._mouse_rotated = False
        self._last_mouse_pos = None

    @Slot()
    def reset(self):
        self.scene.clear()

        self.candidates = []
        self.selected_candidate = None
        self.best_candidates = {}
        self.played_tiles = {}
        self.open_coords_list = []
        self.selected_open_coords = None
        self.watched_open_coords_list = {}
        self.open_coordinates_enabled = False
        self.open_coordinates_auto_toggled = False
        self._mouse_moved = False
        self._mouse_rotated = False
        self._last_mouse_pos = None

        self.centerOn(QPointF(0, 0))

    @Slot(tuple)
    def handle_updated_session(self, session):
        self.reset_candidates()

        self.played_tiles = session.played_tiles
        self.open_coords_list = session.open_coords
        self.selected_open_coords = None
        self.watched_open_coords_list = session.watched_open_coords

    @Slot(tuple)
    def handle_update_candidates(self, event):
        self.reset_candidates()
        self.candidates, self.best_candidates, self.open_coords_list = event

        self.show_candidates()

    @Slot(int)
    def handle_update_candidate_selection(self, selected_index):
        if selected_index < 0 or selected_index >= len(self.candidates):
            return

        if self.selected_candidate == self.candidates[selected_index]:
            return

        previous_coordinates = None
        if self.selected_candidate is not None:
            previous_coordinates = self.selected_candidate.tile.coordinates

        self.selected_candidate = self.candidates[selected_index]
        self.update_items(
            old_coords=previous_coordinates,
            new_coords=self.selected_candidate.tile.coordinates,
        )
        self.coordinates_selected.emit(self.selected_candidate.tile.coordinates)

    @Slot(tuple)
    def handle_update_coordinates_selection(self, coordinates):
        if self.selected_open_coords == coordinates:
            return

        if self.selected_candidate is None and coordinates in self.open_coords_list:
            prev_selected_open_coords = self.selected_open_coords
            self.selected_open_coords = coordinates
            self.update_items(
                old_coords=prev_selected_open_coords,
                new_coords=coordinates,
                consider_neighbors=False,
            )

            if not self.open_coordinates_enabled:
                # automatically turn on showing coordinates,
                # otherwise the selected coordinate will not be highlighted (visible) in map
                self.open_coordinates_enabled = True
                self.open_coordinates_auto_toggled = True
                self.update_visibility_of_all_open_coords()

        if (
            self.selected_candidate is not None
            and self.selected_candidate.tile.coordinates != coordinates
            and coordinates in self.best_candidates
        ):
            candidate_idx, candidate = self.best_candidates[coordinates]
            self.candidate_selected.emit(candidate_idx)

    @Slot()
    def refresh(self):
        self.scene.clear()
        for tile in self.played_tiles.values():
            self.refresh_item(tile.coordinates)
        # show best candidate per coordinate (if available)
        for candidate_idx, candidate in self.best_candidates.values():
            self.draw_candidate(candidate)
        if self.selected_candidate is not None:
            self.refresh_candidate(self.selected_candidate)
        self.update_scene_rect()

    @Slot(tuple)
    def handle_placed_tile(self, tile):
        self.update_items(new_coords=tile.coordinates)
        self.reset_auto_toggle_visibility_open_coords()
        self.update_visibility_of_all_open_coords()

    @Slot(tuple)
    def handle_undone_tile(self, tile):
        self.update_items(old_coords=tile.coordinates)
        self.reset_auto_toggle_visibility_open_coords()
        self.update_visibility_of_all_open_coords()

    @Slot()
    def handle_watch_open_coordinates(self):
        if self.selected_candidate is not None:
            self.trigger_watch_coordinates.emit(
                self.selected_candidate.tile.coordinates
            )
        elif self.selected_open_coords is not None:
            self.trigger_watch_coordinates.emit(self.selected_open_coords)

    @Slot(tuple)
    def handle_watched_coordinates_changed(self, event):
        watched_open_coords, coordinates, added = event
        self.watched_open_coords_list = watched_open_coords
        if added:
            self.update_items(new_coords=coordinates, consider_neighbors=False)
        else:
            self.update_items(old_coords=coordinates, consider_neighbors=False)

    @Slot()
    def handle_toggle_open_coords_display(self):
        if self.open_coordinates_enabled:
            self.clear_coordinates_selection()

        self.open_coordinates_enabled = not self.open_coordinates_enabled
        self.update_visibility_of_all_open_coords()

    @Slot()
    def clear_coordinates_selection(self):
        # never clear selection when we are displaying candidates
        # as we always have a candidate highlighted
        if self.selected_candidate is not None:
            return

        if self.selected_open_coords is None:
            return

        self.reset_auto_toggle_visibility_open_coords()

        prev_coordinates = self.selected_open_coords
        self.selected_open_coords = None
        self.update_items(old_coords=prev_coordinates, consider_neighbors=False)
        self.update_visibility_of_all_open_coords()
        self.trigger_clear_coordinates_selection.emit()

    @Slot()
    def center_at_current_selection(self):
        if self.selected_candidate is not None:
            self.centerOn(
                to_scene_coordinates(self.selected_candidate.tile.coordinates)
            )
            self.coordinates_selected.emit(
                self.selected_candidate.tile.coordinates
            )
        elif self.selected_open_coords is not None:
            self.centerOn(to_scene_coordinates(self.selected_open_coords))
            self.coordinates_selected.emit(self.selected_open_coords)

    def remove_items_at_coordinates(self, coordinates):
        scene_coords = to_scene_coordinates(coordinates)
        items = self.scene.items(scene_coords)
        for item in items:
            if item.contains_point(scene_coords):
                self.scene.removeItem(item)

    def toggle_visibility_of_items_at_coordinates(self, coordinates, instance_type, visible):
        scene_coords = to_scene_coordinates(coordinates)
        items = self.scene.items(scene_coords)
        # toggle
        if len(items) > 0:
            for item in items:
                if isinstance(item, instance_type) and item.contains_point(
                    scene_coords
                ):
                    item.setVisible(visible)
        # first time drawing
        else:
            self.refresh_item(coordinates)

    def refresh_candidate(self, candidate):
        if candidate == self.selected_candidate:
            self.draw_tile(
                self.selected_candidate.tile,
                candidate=self.selected_candidate,
                highlight=True,
            )
        else:
            self.draw_candidate(candidate)

    def show_candidates(self):
        if self.open_coordinates_enabled:
            # automatically turn off showing coordinates, as we are displaying candidates
            self.open_coordinates_enabled = False
            self.open_coordinates_auto_toggled = True

        self.update_visibility_of_all_open_coords()

        # show best candidate per coordinate
        for candidate_idx, candidate in self.best_candidates.values():
            self.draw_candidate(candidate)

    def reset_candidates(self):
        for candidate_idx, candidate in self.best_candidates.values():
            self.remove_items_at_coordinates(candidate.tile.coordinates)

        selected_candidate_coordinates = None
        if self.selected_candidate is not None:
            selected_candidate_coordinates = self.selected_candidate.tile.coordinates

        self.candidates = []
        self.selected_candidate = None
        self.best_candidates = {}

        self.update_items(old_coords=selected_candidate_coordinates)

    def refresh_tile(self, tile):
        if self.layer_selection == UIConstants.Layer.LANDSCAPES:
            # elevate tiles that are direct neighbors of the current candidate
            if (
                self.selected_candidate is not None
                and tile.coordinates
                in self.selected_candidate.tile.get_neighbor_coords_values()
            ):
                self.draw_tile(tile, elevate=True)
            else:
                self.draw_tile(tile)
        elif self.layer_selection == UIConstants.Layer.PLACEMENT_RATINGS:
            if (
                self.selected_candidate is not None
                and tile.coordinates
                in self.selected_candidate.tile.get_neighbor_coords_values()
            ):
                self.draw_placement_rated_tile(tile, self.selected_candidate)
            else:
                self.draw_placement_rated_tile(tile)

    def update_visibility_of_all_open_coords(self):
        for open_tile_coords in self.open_coords_list:
            self.toggle_visibility_of_items_at_coordinates(
                open_tile_coords,
                instance_type=OpenCoordinateItem,
                visible=self.open_coordinates_enabled,
            )

    def refresh_open_coords(self, coordinates):
        if coordinates is None:
            return

        if coordinates == self.selected_open_coords:
            self.draw_open_coordinates(
                coordinates, highlight=True, visible=self.open_coordinates_enabled
            )
        elif coordinates in self.watched_open_coords_list:
            self.draw_open_coordinates(
                coordinates, elevate=True, visible=self.open_coordinates_enabled
            )
        elif coordinates in self.open_coords_list:
            self.draw_open_coordinates(
                coordinates, visible=self.open_coordinates_enabled
            )

    def reset_auto_toggle_visibility_open_coords(self):
        # possibly reset
        if self.open_coordinates_auto_toggled:
            self.open_coordinates_enabled = not self.open_coordinates_enabled
            self.open_coordinates_auto_toggled = False

    def update_items(self, old_coords=None, new_coords=None, consider_neighbors=True):
        def get_neighbor_coords(coords):
            if coords is not None:
                # the neighbor_coordinates also contain the coordinate of the center itself
                if coords in self.played_tiles:
                    return self.played_tiles[coords].get_neighbor_coords_values()
                elif (
                    self.selected_candidate is not None
                    and coords == self.selected_candidate.tile.coordinates
                ):
                    return self.selected_candidate.tile.get_neighbor_coords_values()
                elif coords in self.best_candidates:
                    candidate_idx, candidate = self.best_candidates[coords]
                    return candidate.tile.get_neighbor_coords_values()
                else:
                    return [
                        Tile.get_coordinates(coords, subsection)
                        for subsection in TileSubsection.get_all_values()
                    ]
            return {}

        # collect the coordinates to refresh
        if consider_neighbors:
            refresh_coordinates = {
                coords: None for coords in get_neighbor_coords(old_coords)
            }
            refresh_coordinates.update(
                {
                    coords: None
                    for coords in get_neighbor_coords(new_coords)
                }
            )
        else:
            refresh_coordinates = {
                coords: None
                for coords in [old_coords, new_coords]
                if coords is not None
            }

        if len(refresh_coordinates) > 0:
            self.refresh_items(refresh_coordinates)
            self.update_scene_rect()

    def refresh_items(self, coordinates_dict):
        for coordinates in coordinates_dict.keys():
            self.refresh_item(coordinates)

    def refresh_item(self, coordinates):
        self.remove_items_at_coordinates(coordinates)

        if coordinates in self.played_tiles:
            self.refresh_tile(self.played_tiles[coordinates])
        elif (
            self.selected_candidate is not None
            and coordinates == self.selected_candidate.tile.coordinates
        ):
            self.refresh_candidate(self.selected_candidate)
        elif coordinates in self.best_candidates:
            candidate_idx, candidate = self.best_candidates[coordinates]
            self.refresh_candidate(candidate)
        elif coordinates in self.open_coords_list:
            self.refresh_open_coords(coordinates)

    def draw_candidate(self, candidate, highlight=False):
        item = CandidateTileItem(
            candidate,
            tile_color=get_candidate_rating_color(self.candidates, candidate),
            highlight=highlight,
        )
        self.scene.addItem(item)

    def draw_tile(self, tile, candidate=None, highlight=False, elevate=False):
        item = LandscapeTileItem(tile, candidate, highlight=highlight, elevate=elevate)
        self.scene.addItem(item)

    def draw_placement_rated_tile(self, tile, neighbor_candidate=None):
        item = PlacementRatedTileItem(tile, neighbor_candidate)
        self.scene.addItem(item)

    def draw_open_coordinates(self, coordinates, highlight=False, elevate=False, visible=True):
        item = OpenCoordinateItem(coordinates, highlight=highlight, elevate=elevate)
        self.scene.addItem(item)
        item.setVisible(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scene_rect()
        self.center_at_current_selection()

    def update_scene_rect(self):
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        items_rect = self.scene.itemsBoundingRect()
        # Expand the scene rect to allow panning within the visible view rect
        extended_scene_rect = items_rect.adjusted(
            -view_rect.width(),
            -view_rect.height(),
            view_rect.width(),
            view_rect.height(),
        )
        self.setSceneRect(extended_scene_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._mouse_rotated = True
            self._last_mouse_pos = event.pos()

        if event.button() == Qt.MiddleButton:
            event = self._clone_with_left_mouse_button(event)

        if event.button() == Qt.LeftButton:
            self._mouse_moved = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mouse_rotated and event.buttons() & Qt.RightButton:
            current_pos = event.pos()
            delta = current_pos - self._last_mouse_pos
            angle = delta.x() * 0.5  # Adjust this value to control the rotation speed
            self.rotate(angle)
            self._last_mouse_pos = current_pos

        if event.buttons() & Qt.MiddleButton:
            event = self._clone_with_left_mouse_button(event)

        if event.buttons() & Qt.LeftButton:
            self._mouse_moved = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._mouse_rotated = False

        if event.button() == Qt.MiddleButton:
            event = self._clone_with_left_mouse_button(event)
        elif event.button() == Qt.LeftButton:
            if not self._mouse_moved:
                # allow candidate selection by click in the map (only left mouse)
                item = self._find_item(self.mapToScene(event.position().toPoint()))

                if isinstance(item, (LandscapeTileItem, CandidateTileItem)):
                    if item.tile.coordinates in self.best_candidates:
                        candidate_idx, candidate = self.best_candidates[
                            item.tile.coordinates
                        ]
                        self.candidate_selected.emit(candidate_idx)
                    self.coordinates_selected.emit(item.tile.coordinates)
                elif isinstance(item, OpenCoordinateItem):
                    # in case of manual selection of an item in map, overwrite auto toggle
                    self.open_coordinates_auto_toggled = False
                    self.coordinates_selected.emit(item.coordinates)
                else:
                    self.clear_coordinates_selection()

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.reset_view()

        # Indicate that the event has been handled to not also trigger mousePressEvent
        event.accept()

    def reset_view(self):
        self.resetTransform()

        if self.selected_candidate is not None:
            self.center_at_current_selection()
        else:
            self.centerOn(self.initial_center)

    def handle_rotation(self, event, on_mouse_over=False):
        if self.selected_candidate is None:
            return False

        if on_mouse_over:
            item = self._find_item(self.mapToScene(event.position().toPoint()))
            if (
                not (
                    isinstance(item, (LandscapeTileItem, CandidateTileItem))
                )
                or item.tile.coordinates != self.selected_candidate.tile.coordinates
            ):
                return False

        # Extract the delta value to determine the direction of the wheel rotation
        delta = event.angleDelta().y()

        if delta > 0:
            self.trigger_rotation.emit((self.selected_candidate, -1))
        else:
            self.trigger_rotation.emit((self.selected_candidate, 1))

        return True

    def handle_zoom(self, event):
        old_pos = self.mapToScene(event.position().toPoint())

        # Determine the zoom factor and scale the view
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)

        new_pos = self.mapToScene(event.position().toPoint())

        # Calculate the translation to keep the position fixed
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def wheelEvent(self, event):
        if self.handle_rotation(event, on_mouse_over=True):
            return

        # rotate when 'Ctrl' is pressed at the same time as the mouse wheel is turned
        if event.modifiers() & Qt.ControlModifier:
            self.handle_rotation(event)
            return

        # otherwise zoom
        self.handle_zoom(event)

    def keyPressEvent(self, event):
        # Watch coordinates
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_W:
            if self.selected_open_coords is not None:
                self.trigger_watch_coordinates.emit(self.selected_open_coords)
            elif self.selected_candidate is not None:
                self.trigger_watch_coordinates.emit(
                    self.selected_candidate.tile.coordinates
                )
        # Unwatch coordinates
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_U:
            if self.selected_open_coords is not None:
                self.trigger_unwatch_coordinates.emit(self.selected_open_coords)
            elif self.selected_candidate is not None:
                self.trigger_unwatch_coordinates.emit(
                    self.selected_candidate.tile.coordinates
                )
        # Toggle session map
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_T:
            self.trigger_toggle_open_coords_display.emit()

        # Camera zoom
        elif event.matches(QKeySequence.ZoomIn) or event.key() == Qt.Key_C:
            self.scale(1.1, 1.1)
        elif event.matches(QKeySequence.ZoomOut) or event.key() == Qt.Key_X:
            self.scale(0.9, 0.9)
        elif event.key() == Qt.Key_Backspace:
            self.reset_view()
        # Camera rotation
        elif event.key() == Qt.Key_Q:
            self.rotate(-5)  # Rotate left by 5 degrees
        elif event.key() == Qt.Key_E:
            self.rotate(5)  # Rotate right by 5 degrees
        # Camera move
        # Map W, A, S, D keys to arrow keys
        elif event.key() == Qt.Key_W:
            arrow_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier)
            QApplication.sendEvent(self, arrow_event)
        elif event.key() == Qt.Key_A:
            arrow_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.NoModifier)
            QApplication.sendEvent(self, arrow_event)
        elif event.key() == Qt.Key_S:
            arrow_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier)
            QApplication.sendEvent(self, arrow_event)
        elif event.key() == Qt.Key_D:
            arrow_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier)
            QApplication.sendEvent(self, arrow_event)
        # Tile rotation
        elif event.key() == Qt.Key_R:
            self.trigger_rotation.emit((self.selected_candidate, 1))
        elif event.key() == Qt.Key_F:
            self.trigger_rotation.emit((self.selected_candidate, -1))
        # Place tile
        elif event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if self.selected_candidate is not None:
                self.confirm_selected_candidate.emit()
        # Toggle session map
        elif event.key() == Qt.Key_T:
            self.trigger_toggle_map_display.emit()
        else:
            super().keyPressEvent(event)

    def _clone_with_left_mouse_button(self, event):
        return QMouseEvent(
            event.type(),
            event.localPos(),
            event.windowPos(),
            event.screenPos(),
            Qt.LeftButton,
            event.buttons() | Qt.LeftButton,
            event.modifiers(),
            event.source(),
        )

    def _find_item(self, scene_coords):
        item = self.scene.itemAt(scene_coords, self.transform())
        if item and item.contains_point(scene_coords):
            return item

        return None


class CandidateNeighborMapView(TileMapView):
    def __init__(self):
        super().__init__(None)
        self.all_played_tiles = {}
        self.setFixedHeight(UIConstants.LOWER_LAYOUT_HEIGHT)
        self.setMinimumWidth(UIConstants.CANDIDATE_NEIGHBOR_MAP_MIN_WIDTH)

    @Slot()
    def refresh(self):
        self.refresh_scene()

    @Slot(tuple)
    def handle_update_candidates(self, event):
        self.candidates, best_candidates, self.open_coords_list = event

    @Slot(int)
    def handle_update_candidate_selection(self, selected_index):
        if 0 <= selected_index < len(self.candidates):
            if self.selected_candidate == self.candidates[selected_index]:
                return
            self.selected_candidate = self.candidates[selected_index]
            self.refresh_scene()

    @Slot(tuple)
    def handle_updated_session(self, session):
        self.candidates = []
        self.selected_candidate = None
        self.played_tiles = session.played_tiles
        self.open_coords_list = session.open_coords
        self.curr_open_coords = None

    def toggle_visibility(self, visible):
        for item in self.items():
            item.setVisible(visible)

    def refresh_scene(self):
        self.scene.clear()
        self.viewport().update()

        if self.selected_candidate is None:
            return

        self.draw_candidate(self.selected_candidate, highlight=True)

        # only draw the direct neighbors of the current candidate
        for tile in self.played_tiles.values():
            if (
                tile.coordinates
                in self.selected_candidate.tile.get_neighbor_coords_values()
            ):
                self.draw_placement_rated_tile(tile, self.selected_candidate)

        self.update_scene_rect()
        self.center_at_current_selection()

    def mousePressEvent(self, event):
        return

    def mouseDoubleClickEvent(self, event):
        return

    def wheelEvent(self, event):
        self.handle_rotation(event, on_mouse_over=True)

    def keyPressEvent(self, event):
        return
