import pytest
from yt2spotify import utils


def test_clean_title_basic():
    assert (
        utils.clean_title("Daft Punk - One More Time (Official Video)")
        == "daft punk one more time"
    )


def test_clean_title_brackets_and_case():
    assert utils.clean_title("[HD] Beyoncé - Halo [Live]") == "beyoncé halo"


def test_parse_artist_track_dash():
    artist, track = utils.parse_artist_track("Daft Punk - One More Time")
    assert artist == "daft punk"
    assert track == "one more time"


def test_parse_artist_track_no_dash():
    artist, track = utils.parse_artist_track("One More Time")
    assert artist is None
    assert track == "one more time"


def test_get_spotify_credentials_env(monkeypatch):
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "uri")
    creds = utils.get_spotify_credentials()
    assert creds == ("id", "secret", "uri")


def test_get_spotify_credentials_missing(monkeypatch):
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "", prepend=False)
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "", prepend=False)
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "", prepend=False)
    # Patch os.getenv to always return None for these keys
    import os as _os

    monkeypatch.setattr(_os, "getenv", lambda k, default=None: None)
    with pytest.raises(RuntimeError):
        utils.get_spotify_credentials()
