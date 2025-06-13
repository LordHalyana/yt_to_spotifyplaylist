import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from yt2spotify import cache

def test_track_cache_set_and_get(tmp_path):
    db_path = tmp_path / "test_cache.sqlite"
    c = cache.TrackCache(str(db_path))
    c.set("artist", "title", "trackid123")
    assert c.get("artist", "title") == "trackid123"
    # Overwrite
    c.set("artist", "title", "trackid456")
    assert c.get("artist", "title") == "trackid456"

def test_track_cache_missing(tmp_path):
    db_path = tmp_path / "test_cache.sqlite"
    c = cache.TrackCache(str(db_path))
    assert c.get("missing", "song") is None

def test_track_cache_clear(tmp_path):
    db_path = tmp_path / "test_cache.sqlite"
    c = cache.TrackCache(str(db_path))
    c.set("a", "b", "id")
    # Remove the row manually since TrackCache has no clear method
    import sqlite3
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("DELETE FROM track_cache")
        conn.commit()
    assert c.get("a", "b") is None
