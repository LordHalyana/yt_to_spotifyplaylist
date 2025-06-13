from yt2spotify import youtube


def test_get_yt_playlist_titles_api_handles_no_api_key(monkeypatch):
    monkeypatch.setattr(
        youtube, "get_yt_playlist_titles_yt_dlp", lambda pid: ["fallback"]
    )
    result = youtube.get_yt_playlist_titles_api("", "playlist_id")
    assert result == ["fallback"]


def test_get_yt_playlist_titles_api_handles_http_error(monkeypatch):
    class DummyHttpError(Exception):
        def __init__(self):
            self.resp = type("resp", (), {"status": 403})()

    def dummy_build(*a, **kw):
        class DummyRequest:
            def list(self, **kwargs):
                class DummyExec:
                    def execute(self):
                        raise DummyHttpError()

                return DummyExec()

        return type(
            "DummyYouTube", (), {"playlistItems": lambda self: DummyRequest()}
        )()

    monkeypatch.setattr(youtube, "build", dummy_build)
    monkeypatch.setattr(
        youtube, "get_yt_playlist_titles_yt_dlp", lambda pid: ["fallback"]
    )
    result = youtube.get_yt_playlist_titles_api("fake_key", "playlist_id")
    assert result == ["fallback"]


def test_get_yt_playlist_titles_api_handles_other_exception(monkeypatch):
    def dummy_build(*a, **kw):
        class DummyRequest:
            def list(self, **kwargs):
                class DummyExec:
                    def execute(self):
                        raise Exception("fail")

                return DummyExec()

        return type(
            "DummyYouTube", (), {"playlistItems": lambda self: DummyRequest()}
        )()

    monkeypatch.setattr(youtube, "build", dummy_build)
    monkeypatch.setattr(
        youtube, "get_yt_playlist_titles_yt_dlp", lambda pid: ["fallback"]
    )
    result = youtube.get_yt_playlist_titles_api("fake_key", "playlist_id")
    assert result == ["fallback"]
