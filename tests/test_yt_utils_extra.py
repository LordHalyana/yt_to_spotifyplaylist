from yt2spotify import yt_utils

def test_get_yt_playlist_titles_yt_dlp_empty(monkeypatch):
    class DummyYDL:
        def __init__(self, opts): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def extract_info(self, playlist_url, download=False):
            return {'entries': []}
    monkeypatch.setattr("yt_dlp.YoutubeDL", DummyYDL)
    titles = yt_utils.get_yt_playlist_titles_yt_dlp("fake_url")
    assert titles == []

def test_get_yt_playlist_titles_yt_dlp_none_titles(monkeypatch):
    class DummyYDL:
        def __init__(self, opts): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def extract_info(self, playlist_url, download=False):
            return {'entries': [{}, {'title': None}]}
    monkeypatch.setattr("yt_dlp.YoutubeDL", DummyYDL)
    titles = yt_utils.get_yt_playlist_titles_yt_dlp("fake_url")
    assert titles == []
