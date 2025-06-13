from yt2spotify import cache

def test_track_cache_case_insensitive(tmp_path):
    db_path = tmp_path / "test_cache.sqlite"
    c = cache.TrackCache(str(db_path))
    c.set("Artist", "Title", "trackid")
    # Should be case-insensitive
    assert c.get("artist", "title") == "trackid"
    assert c.get("ARTIST", "TITLE") == "trackid"

def test_track_cache_overwrite(tmp_path):
    db_path = tmp_path / "test_cache.sqlite"
    c = cache.TrackCache(str(db_path))
    c.set("A", "B", "id1")
    c.set("A", "B", "id2")
    assert c.get("A", "B") == "id2"
