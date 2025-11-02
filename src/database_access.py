import sqlite3
from datetime import datetime

from typing import List, Tuple

import pandas as pd

from src.side import Side
from src.side_type import SIDE_TYPE_TO_CHAR

class DatabaseAccess():
    """
    Class to access the database that holds information for the session.
    """

    def __init__(self, database=None):
        """
        Creates a database access object.

        Args:
            `database` is the path to the database.
        """
        self.conn = None
        self.cursor = None

        self.database = database
        if self.database is not None:
            self.create_tables()

    def __del__(self):
        """
        Destructor to ensure proper cleanup of resources when the object is destroyed.
        """
        self.close_connection()

    def __enter__(self):
        """
        Method called when entering a context managed block (using 'with' statement).
        Returns self to allow operations within the context.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Method called when exiting a context managed block (using 'with' statement).
        Ensures that the database connection is closed upon exiting the context.
        """
        self.close_connection()

    def start_connection(self):
        """
        Opens the database connection and stores the cursor, if not yet present.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
        """
        if self.database is None:
            raise RuntimeError("Database has not been loaded")

        if self.conn is not None or self.cursor is not None:
            return  # Database is already loaded

        self.conn = sqlite3.connect(self.database)
        self.cursor = self.conn.cursor()

    def close_connection(self):
        """
        Closes the database connection and cursor if they are open.
        """
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """
        Creates necessary tables in the database if they do not already exist.
        """
        self.start_connection()
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name VARCHAR(255),
                                save_date DATE
                                )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS tiles (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                side_type_seq VARCHAR(6),
                                center_type VARCHAR(1),
                                quest_type VARCHAR(1),
                                session_id INTEGER,
                                FOREIGN KEY (session_id) REFERENCES sessions(id)
                                )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS placed_tiles (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                coordinates VARCHAR(15),
                                num_perfect_sides INTEGER,
                                num_imperfect_sides INTEGER,
                                num_unknown_sides INTEGER,
                                tile_id INTEGER,
                                FOREIGN KEY (tile_id) REFERENCES tiles(id)
                                )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS watched_coordinates (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                coordinates VARCHAR(15),
                                session_id INTEGER,
                                FOREIGN KEY (session_id) REFERENCES sessions(id)
                                )''')
            self.conn.commit()
        finally:
            self.close_connection()

    def fetch_all_sessions(self) -> pd.DataFrame:
        """
        Fetches all sessions from the database and returns them as a Pandas DataFrame.

        Returns:
            DataFrame containing session information with columns:
            'id', 'name', 'save_date', 'number_of_tiles'.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by Pandas or SQLite operations.
        """
        self.start_connection()

        try:
            query_sessions = '''SELECT s.id, s.name, save_date, COUNT(t.id) AS number_of_tiles
                                FROM sessions s
                                JOIN tiles t ON s.id = t.session_id
                                GROUP BY s.id'''
            return pd.read_sql_query(query_sessions, self.conn)
        finally:
            self.close_connection()

    def find_session_ids_by_name(self, session_name) -> List[int]:
        """
        Finds session IDs in the database by session name.

        Args:
            session_name (str): The name of the session to search for.

        Returns:
            List of session IDs found in the database for the given session name.
            Returns an empty list if no sessions match the name.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite operations.
        """
        self.start_connection()

        self.cursor.execute('SELECT id FROM sessions WHERE name = ?', (session_name,))
        results = self.cursor.fetchall()
        if results:
            return [result[0] for result in results]
        return []

    def save_session(self, name, session, save_watched_coordinates=True) -> int:
        """
        Saves a session to the database.

        Args:
            name (str): The name of the session.
            session (Session): The session object containing session data.
            save_watched_coordinates (bool, optional): Whether to save watched coordinates.
                                                       Defaults to True.

        Returns:
            The ID of the saved session.

        Raises:
            ValueError: If `name` is None or empty.
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        try:
            if name is None or not name:
                raise ValueError("Session needs a name")

            # Start a transaction
            self.cursor.execute('BEGIN')

            try:
                # Get the current date as 'YYYY-MM-DD'
                date = datetime.now().date().strftime('%Y-%m-%d')
                self.cursor.execute('''
                    INSERT INTO sessions (name, save_date)
                    VALUES (?, ?)
                ''', (name, date))
                session_id = self.cursor.lastrowid

                for coordinates, tile in session.played_tiles.items():
                    self.add_placed_tile(session_id, tile, commit_to_database=False)

                if save_watched_coordinates:
                    for coordinates in session.watched_open_coords.keys():
                        self.add_watched_coordinates(session_id, coordinates)

                self.cursor.execute('COMMIT')
                return session_id
            except Exception as e:
                # Roll back the transaction if any error occurs
                self.cursor.execute('ROLLBACK')
                raise e
        finally:
            self.close_connection()

    def fill_session_tiles(self, session_id, played_tiles) -> int:
        """
        Fills a session with new played tiles in the database.

        Args:
            session_id (int): The ID of the session to update.
            played_tiles (dict): Dictionary of coordinates and tiles to add to the session.

        Returns:
            The ID of the updated session.

        Raises:
            ValueError: If no session exists with the given `session_id`.
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        try:
            self.cursor.execute('BEGIN')

            try:
                # Verify session exists
                self.cursor.execute('SELECT id FROM sessions WHERE id = ?',
                                    (int(session_id),))
                if not self.cursor.fetchone():
                    raise ValueError(f"No session with id {session_id}")

                # Update session date ('YYYY-MM-DD')
                date = datetime.now().date().strftime('%Y-%m-%d')
                self.cursor.execute('UPDATE sessions SET save_date = ? WHERE id = ?',
                                    (date, session_id))

                for tile in played_tiles.values():
                    self.add_placed_tile(session_id, tile, commit_to_database=False)

                self.cursor.execute('COMMIT')
                return session_id
            except Exception as e:
                # Roll back the transaction if any error occurs
                self.cursor.execute('ROLLBACK')
                raise e
        finally:
            self.close_connection()

    def load_session(self, session_id) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads session data from the database based on session ID.

        Args:
            id (int): The ID of the session to load.

        Returns:
            A tuple containing two DataFrames:
                - data: DataFrame containing the tiles in the session
                - watched_coords: DataFrame of watched coordinates (if existing)

        Raises:
            ValueError: If no session exists with the given `id`.
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or Pandas operations.
        """
        self.start_connection()

        try:
            query_tiles = 'SELECT * FROM tiles'
            query_placed_tiles = 'SELECT * FROM placed_tiles'
            query_watched_coords = 'SELECT * FROM watched_coordinates WHERE session_id = ?'
            query_sessions = 'SELECT * FROM sessions WHERE id = ?'

            df_tiles = pd.read_sql_query(query_tiles, self.conn)
            df_placed_tiles = pd.read_sql_query(query_placed_tiles, self.conn)
            df_watched_coords = pd.read_sql_query(query_watched_coords, self.conn,
                                                  params=(int(session_id),))
            df_sessions = pd.read_sql_query(query_sessions, self.conn, params=(int(session_id),))

            # Merge DataFrames based on key/foreign key pairs
            merged_df = pd.merge(df_tiles, df_placed_tiles,
                                 left_on='id', right_on='tile_id',
                                 suffixes=('_tile', '_placed'))
            merged_df = pd.merge(merged_df, df_sessions,
                                 left_on='session_id', right_on='id',
                                 suffixes=('_merged', '_session'))

            merged_df.drop(columns=["id_tile", "id", "name", "id_placed"], inplace=True)
            merged_df.set_index("tile_id", inplace=True)

            return (merged_df, df_watched_coords)
        finally:
            self.close_connection()

    def add_placed_tile(self, session_id, tile, commit_to_database=True):
        """
        Adds a placed tile to the database for a session.

        Args:
            session_id (int): The ID of the session to add the tile to.
            tile (Tile): The Tile object to add.
            commit_to_database (bool, optional):
                Whether to commit changes immediately to the database.
                Defaults to True.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        self.cursor.execute(
            '''
            INSERT INTO tiles (side_type_seq, center_type, quest_type, session_id)
            VALUES (?, ?, ?, ?)
            ''',
            (tile.get_side_type_seq(),
                SIDE_TYPE_TO_CHAR[tile.get_center().type],
                SIDE_TYPE_TO_CHAR[tile.quest.type] if tile.quest is not None else "",
                session_id))
        tile_id = self.cursor.lastrowid

        side_numbers = [tile.get_num_sides(type)
                        for type in [Side.Placement.PERFECT_MATCH,
                                    Side.Placement.IMPERFECT_MATCH,
                                    Side.Placement.UNKNOWN_MATCH]]

        self.cursor.execute('''
                            INSERT INTO placed_tiles (
                            coordinates,
                            num_perfect_sides, num_imperfect_sides, num_unknown_sides,
                            tile_id)
                            VALUES (?, ?, ?, ?, ?)
                            ''',
                            (str(tile.coordinates), *side_numbers, tile_id))
        if commit_to_database:
            # Update session date ('YYYY-MM-DD')
            date = datetime.now().date().strftime('%Y-%m-%d')
            self.cursor.execute('UPDATE sessions SET save_date = ? WHERE id = ?',
                                (date, session_id))
            self.conn.commit()

    def remove_last_placed_tile(self, session_id) -> bool:
        """
        Removes the last placed tile from the database for a session.

        Args:
            session_id (int): The ID of the session to remove the last placed tile from.

        Returns:
            True if the tile was successfully removed, False otherwise.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        # Find the most recently added placed tile for the given session
        self.cursor.execute('''SELECT pt.id, pt.tile_id FROM placed_tiles pt
                            JOIN tiles t ON pt.tile_id = t.id
                            WHERE t.session_id = ?
                            ORDER BY pt.id DESC
                            LIMIT 1''', (session_id,))
        result = self.cursor.fetchone()
        if result:
            placed_tile_id, tile_id = result
            # Delete the most recently added placed tile and corresponding tile
            self.cursor.execute('DELETE FROM placed_tiles WHERE id = ?',
                                (placed_tile_id,))
            self.cursor.execute('DELETE FROM tiles WHERE id = ?',
                                (tile_id,))
            self.conn.commit()
            return True
        return False

    def add_watched_coordinates(self, session_id, coordinates):
        """
        Adds watched coordinates to the database for a session.

        Args:
            session_id (int): The ID of the session to add watched coordinates to.
            coordinates (tuple): The coordinates to add.

        Raises:
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        self.cursor.execute('''
                            INSERT INTO watched_coordinates (
                                coordinates,
                                session_id)
                            VALUES (?, ?)
                            ''',
                            (str(coordinates), session_id))

    def delete_session_and_related(self, session_id, leave_empty_session=False):
        """
        Deletes a session and its related data from the database.

        Args:
            session_id (int): The ID of the session to delete.
            leave_empty_session (bool, optional):
                Whether to leave the session in the database
                with empty related data (tiles, watched coordinates).
                Defaults to False.

        Raises:
            ValueError: If no session exists with the given `session_id`.
            RuntimeError: If the database path (`self.database`) is `None`.
            Any other exceptions raised by SQLite or internal methods.
        """
        self.start_connection()

        try:
            self.cursor.execute('BEGIN')

            try:
                # Verify session exists
                self.cursor.execute('SELECT id FROM sessions WHERE id = ?',
                                    (int(session_id),))
                if not self.cursor.fetchone():
                    raise ValueError(f"No session with id {session_id}")

                # Delete placed_tiles that reference the tiles of the session
                self.cursor.execute('''
                    DELETE FROM placed_tiles
                    WHERE tile_id IN (
                        SELECT id FROM tiles WHERE session_id = ?
                    )
                ''', (int(session_id),))

                # Delete tiles that reference the session
                self.cursor.execute('''
                    DELETE FROM tiles
                    WHERE session_id = ?
                ''', (int(session_id),))

                # Delete watched coordinates that reference the session
                self.cursor.execute('''
                    DELETE FROM watched_coordinates
                    WHERE session_id = ?
                ''', (int(session_id),))

                if not leave_empty_session:
                    # Delete the session
                    self.cursor.execute('''
                        DELETE FROM sessions
                        WHERE id = ?
                    ''', (int(session_id),))

                self.cursor.execute('COMMIT')
            except Exception as e:
                # Rollback the transaction in case of error
                self.cursor.execute('ROLLBACK')
                raise e
        finally:
            self.close_connection()
