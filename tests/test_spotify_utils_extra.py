import pytest
from yt2spotify import spotify_utils

def test_spotify_search_empty_result():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": []}}
    sp = DummySpotify()
    result = spotify_utils.spotify_search(sp, "query")
    assert isinstance(result, dict)
    assert result["tracks"]["items"] == []

def test_spotify_search_non_dict():
    class DummySpotify:
        def search(self, q, type, limit):
            return 123
    sp = DummySpotify()
    result = spotify_utils.spotify_search(sp, "query")
    assert result == {}
