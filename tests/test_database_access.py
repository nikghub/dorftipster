import pytest
import os

from src.database_access import DatabaseAccess

def test_no_connection():
    database_access = DatabaseAccess()

    with pytest.raises(RuntimeError):
        database_access.start_connection()

    with pytest.raises(RuntimeError):
        database_access.fetch_all_sessions()

    with pytest.raises(RuntimeError):
        database_access.load_session("some_id")

    with pytest.raises(RuntimeError):
        database_access.save_session("some name", None)

    with pytest.raises(RuntimeError):
        database_access.delete_session_and_related("some name")

def test_invalid_input():
    database = "./tests/data/__test_save_load__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with DatabaseAccess(database) as database_access:
        database_access.start_connection()
        database_access.start_connection()  # should have no effect
        database_access.close_connection()

        with pytest.raises(ValueError):
            database_access.save_session("", None)

        with pytest.raises(ValueError):
            database_access.save_session(None, None)

        with pytest.raises(AttributeError):
            database_access.save_session("some name", None)

        with pytest.raises(ValueError):
            database_access.delete_session_and_related("5")

        with pytest.raises(ValueError):
            database_access.fill_session_tiles(5, None)

    os.remove(database)

def test_find_session():
    database = "./tests/data/__test_save_load__.db"

    if os.path.exists(database):
        os.remove(database)  # ensure a clean start

    with DatabaseAccess(database) as database_access:
        assert not database_access.find_session_ids_by_name("some name")

    os.remove(database)