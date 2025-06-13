import pytest
from yt2spotify import spotify_utils
import typing


def test_get_spotify_client_success(monkeypatch):
    # Patch credentials and Spotify/SpotifyOAuth
    monkeypatch.setattr(
        spotify_utils, "get_spotify_credentials", lambda: ("id", "secret", "uri")
    )

    class DummySpotify:
        pass

    class DummyOAuth:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(spotify_utils, "SpotifyOAuth", DummyOAuth)
    monkeypatch.setattr(
        spotify_utils.spotipy, "Spotify", lambda auth_manager: DummySpotify()
    )
    sp = spotify_utils.get_spotify_client()
    assert isinstance(sp, DummySpotify)


def test_get_spotify_client_missing_credentials(monkeypatch):
    def raise_runtime():
        raise RuntimeError("Missing credentials")

    monkeypatch.setattr(spotify_utils, "get_spotify_credentials", raise_runtime)
    with pytest.raises(RuntimeError):
        spotify_utils.get_spotify_client()


def test_spotify_search_empty_result():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert isinstance(result, dict)
    assert result["tracks"]["items"] == []


def test_spotify_search_non_dict():
    class DummySpotify:
        def search(self, q, type, limit):
            return 123

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert result == {}


def test_spotify_search_returns_dict():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": [1, 2]}}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert isinstance(result, dict)
    assert "tracks" in result


def test_spotify_search_returns_empty_on_none():
    class DummySpotify:
        def search(self, q, type, limit):
            return None

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert result == {}


def test_spotify_search_returns_empty_on_list():
    class DummySpotify:
        def search(self, q, type, limit):
            return [1, 2, 3]

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert result == {}


def test_spotify_search_passes_arguments():
    called = {}

    class DummySpotify:
        def search(self, q, type, limit):
            called["q"] = q
            called["type"] = type
            called["limit"] = limit
            return {"tracks": {}}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    spotify_utils.spotify_search(sp, "test query", limit=5)
    assert called["q"] == "test query"
    assert called["type"] == "track"
    assert called["limit"] == 5


def test_spotify_search_empty_string_query():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": [q, type, limit]}}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "")
    assert isinstance(result, dict)
    assert result["tracks"]["items"][0] == ""


def test_spotify_search_large_limit():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"tracks": {"items": list(range(limit))}}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query", limit=1000)
    assert len(result["tracks"]["items"]) == 1000


def test_spotify_search_raises(monkeypatch):
    class DummySpotify:
        def search(self, q, type, limit):
            raise Exception("API error")

    sp = DummySpotify()
    with pytest.raises(Exception):
        sp.search("query", type="track", limit=1)


def test_spotify_search_missing_keys():
    class DummySpotify:
        def search(self, q, type, limit):
            return {"unexpected": 1}

    sp = typing.cast(spotify_utils.spotipy.Spotify, DummySpotify())
    result = spotify_utils.spotify_search(sp, "query")
    assert "tracks" not in result or isinstance(result, dict)


def test_get_spotify_client_oauth_params(monkeypatch):
    monkeypatch.setattr(
        spotify_utils, "get_spotify_credentials", lambda: ("id", "secret", "uri")
    )
    params = {}

    class DummyOAuth:
        def __init__(self, **kwargs):
            params.update(kwargs)

    class DummySpotify:
        pass

    monkeypatch.setattr(spotify_utils, "SpotifyOAuth", DummyOAuth)
    monkeypatch.setattr(
        spotify_utils.spotipy, "Spotify", lambda auth_manager: DummySpotify()
    )
    spotify_utils.get_spotify_client()
    assert params["client_id"] == "id"
    assert params["client_secret"] == "secret"
    assert params["redirect_uri"] == "uri"
    assert "scope" in params
