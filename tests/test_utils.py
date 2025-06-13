import pytest
from yt2spotify import utils


def test_clean_title_basic():
    assert (
        utils.clean_title("Daft Punk - One More Time (Official Video)")
        == "daft punk one more time"
    )


def test_clean_title_brackets_and_case():
    assert utils.clean_title("[HD] Beyoncé - Halo [Live]") == "beyoncé halo"


def test_clean_title_special_chars():
    assert (
        utils.clean_title("Daft Punk – One More Time [HD] (Live)")
        == "daft punk one more time"
    )
    assert utils.clean_title("A - B (Remix) [Official]") == "a b"
    assert utils.clean_title("A   B   C") == "a b c"
    assert utils.clean_title("") == ""


def test_parse_artist_track_dash():
    artist, track = utils.parse_artist_track("Daft Punk - One More Time")
    assert artist == "daft punk"
    assert track == "one more time"


def test_parse_artist_track_no_dash():
    artist, track = utils.parse_artist_track("One More Time")
    assert artist is None
    assert track == "one more time"


def test_parse_artist_track_various_dashes():
    # en dash, em dash, minus, bullet, etc.
    for dash in ["–", "—", "−", "•", "·", "‧", "‐", "‑", "‒", "―", "|", "/"]:
        artist, track = utils.parse_artist_track(f"Artist {dash} Track")
        assert artist == "artist"
        assert track == "track"


def test_parse_artist_track_trailing_info():
    artist, track = utils.parse_artist_track("Artist - Track (Live 2020) [HD]")
    assert artist == "artist"
    assert track == "track"
    artist, track = utils.parse_artist_track("Artist - Track (Remastered 2019)")
    assert artist == "artist"
    assert track == "track"


def test_parse_artist_track_feat():
    artist, track = utils.parse_artist_track(
        "Artist (feat. Someone) - Track ft. Another"
    )
    assert artist == "artist"
    assert track == "track"


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


def test_validate_json_entries(tmp_path):
    path = tmp_path / "test.json"
    path.write_text('[{"a":1,"b":2},{"a":3,"b":4}]')
    utils.validate_json_entries(str(path), {"a", "b"})
    path.write_text('[{"a":1}]')
    with pytest.raises(AssertionError):
        utils.validate_json_entries(str(path), {"a", "b"})


def test_validate_no_duplicates(tmp_path):
    path = tmp_path / "test.json"
    path.write_text('[{"a":1,"b":2},{"a":3,"b":4}]')
    utils.validate_no_duplicates(str(path), {"a", "b"})
    path.write_text('[{"a":1,"b":2},{"a":1,"b":2}]')
    with pytest.raises(AssertionError):
        utils.validate_no_duplicates(str(path), {"a", "b"})
