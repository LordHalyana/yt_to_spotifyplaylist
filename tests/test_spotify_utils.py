from yt2spotify import spotify_utils

def test_spotify_search_returns_dict():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": [1, 2, 3]}}
    sp = DummySpotify()
    result = spotify_utils.spotify_search(sp, "query")
    assert isinstance(result, dict)
    assert "tracks" in result

def test_spotify_search_returns_empty_on_non_dict():
    class DummySpotify:
        def search(self, q, type, limit):
            return None
    sp = DummySpotify()
    result = spotify_utils.spotify_search(sp, "query")
    assert result == {}

def test_get_spotify_client(monkeypatch):
    monkeypatch.setattr(spotify_utils, "get_spotify_credentials", lambda: ("id", "secret", "uri"))
    class DummySpotify:
        pass
    class DummyOAuth:
        def __init__(self, **kwargs):
            pass
    monkeypatch.setattr(spotify_utils, "SpotifyOAuth", DummyOAuth)
    monkeypatch.setattr(spotify_utils.spotipy, "Spotify", lambda auth_manager: DummySpotify())
    sp = spotify_utils.get_spotify_client()
    assert isinstance(sp, DummySpotify)
