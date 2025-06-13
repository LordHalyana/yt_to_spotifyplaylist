import pytest
from yt2spotify import yt_utils


def test_get_yt_playlist_titles_yt_dlp(monkeypatch):
    class DummyYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def extract_info(self, playlist_url, download=False):
            return {
                "entries": [
                    {"title": "Song 1"},
                    {"title": "Song 2"},
                    {"title": None},
                ]
            }

    monkeypatch.setattr("yt2spotify.yt_utils.yt_dlp.YoutubeDL", DummyYDL)
    titles = yt_utils.get_yt_playlist_titles_yt_dlp("fake_url")
    assert titles == ["Song 1", "Song 2"]


def test_get_yt_playlist_titles_api_not_implemented():
    with pytest.raises(NotImplementedError):
        yt_utils.get_yt_playlist_titles_api("fake_url", "fake_key")
