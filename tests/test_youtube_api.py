from yt2spotify import youtube


def test_get_yt_playlist_titles_api_success(monkeypatch):
    # Patch build to simulate YouTube API returning two pages
    class DummyRequest:
        def __init__(self, items, next_token=None):
            self._items = items
            self._next = next_token

        def list(self, **kwargs):
            class DummyExec:
                def __init__(self, items, next_token):
                    self._items = items
                    self._next = next_token

                def execute(self):
                    return {"items": self._items, "nextPageToken": self._next}

            return DummyExec(self._items, self._next)

    class DummyYouTube:
        def __init__(self):
            self.calls = 0

        def playlistItems(self):
            self.calls += 1
            if self.calls == 1:
                return DummyRequest(
                    [{"snippet": {"title": "Song1"}}], next_token="page2"
                )
            else:
                return DummyRequest([{"snippet": {"title": "Song2"}}], next_token=None)

    monkeypatch.setattr(youtube, "build", lambda *a, **kw: DummyYouTube())
    titles = youtube.get_yt_playlist_titles_api("fake_key", "playlist_id")
    assert titles == ["Song1", "Song2"]


def test_get_yt_playlist_titles_api_url_extract(monkeypatch):
    # Patch build to check playlistId extraction from URL
    class DummyRequest:
        def list(self, **kwargs):
            class DummyExec:
                def execute(self):
                    return {
                        "items": [{"snippet": {"title": "SongX"}}],
                        "nextPageToken": None,
                    }

            return DummyExec()

    class DummyYouTube:
        def playlistItems(self):
            return DummyRequest()

    monkeypatch.setattr(youtube, "build", lambda *a, **kw: DummyYouTube())
    url = "https://youtube.com/playlist?list=PL123"
    titles = youtube.get_yt_playlist_titles_api("fake_key", url)
    assert titles == ["SongX"]
