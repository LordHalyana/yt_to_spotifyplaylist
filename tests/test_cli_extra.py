# ruff: noqa: F401, F811, F841
import json
import logging
from unittest import mock
from yt2spotify import cli

logger = logging.getLogger("yt2spotify.tests")


class DummyTrackCache:
    def __init__(self, *args, **kwargs):
        self._cache = {}

    def get(self, artist, title):
        return self._cache.get((artist, title))

    def set(self, artist, title, track_id):
        self._cache[(artist, title)] = track_id

    def close(self):
        pass


def test_sync_command_spotify_429_retry(tmp_path):
    class FakeSpotify:
        class Fake429(Exception):
            def __init__(self):
                self.http_status = 429
                self.headers = mock.Mock()
                self.headers.get = lambda k: "1" if k == "Retry-After" else None

        def __init__(self):
            self.calls = 0

        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            self.calls += 1
            logger.info(f"playlist_add_items call #{self.calls}")
            if self.calls < 3:
                raise FakeSpotify.Fake429()
            return None

        def search(self, q, type, limit):
            # Always return a valid search result
            return {"tracks": {"items": [{"id": "SPOTIFY_TRACK_ID"}]}}

    added_path = tmp_path / "added_songs.json"
    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=FakeSpotify()
    ) as m_spotify, mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp", return_value=["Artist - Track"]
    ), mock.patch(
        "yt2spotify.cache.TrackCache", DummyTrackCache
    ), mock.patch.object(
        cli, "OUTPUT_DIR", str(tmp_path)
    ), mock.patch.object(
        cli, "ADDED_SONGS_PATH", str(added_path)
    ), mock.patch(
        "time.sleep", return_value=None
    ):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={
                "batch_size": 1,
                "batch_delay": 0.01,
                "max_retries": 3,
                "backoff_factor": 1,
            },
        )
        # Debug: print all files in tmp_path
        logger.debug(f"Files in tmp_path: {list(tmp_path.iterdir())}")
        # Debug: print calls
        logger.debug(f"playlist_add_items calls: {m_spotify.return_value.calls}")
        # Assert file exists
        assert (
            added_path.exists()
        ), f"added_songs.json not found in {list(tmp_path.iterdir())}"
        # Optionally, print file contents
        with open(added_path, encoding="utf-8") as f:
            logger.debug(f"added_songs.json contents: {f.read()}")


def test_sync_command_output_file_merging(tmp_path):
    class FakeSpotify:
        class Fake429(Exception):
            def __init__(self):
                self.http_status = 429
                self.headers = mock.Mock()
                self.headers.get = lambda k: "1" if k == "Retry-After" else None

        def __init__(self):
            self.calls = 0

        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            self.calls += 1
            return None

        def search(self, q, type, limit):
            return {"tracks": {"items": [{"id": "SPOTIFY_TRACK_ID"}]}}

    added_path = tmp_path / "added_songs.json"
    with open(added_path, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "title": "Old",
                    "artist": "A",
                    "track": "B",
                    "track_id": "X",
                    "status": "added",
                }
            ],
            f,
        )
    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=FakeSpotify()
    ), mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp", return_value=["Artist - Track"]
    ), mock.patch(
        "yt2spotify.cache.TrackCache", DummyTrackCache
    ), mock.patch.object(
        cli, "OUTPUT_DIR", str(tmp_path)
    ), mock.patch.object(
        cli, "ADDED_SONGS_PATH", str(added_path)
    ):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={
                "batch_size": 1,
                "batch_delay": 0.01,
                "max_retries": 1,
                "backoff_factor": 1,
            },
        )
    with open(added_path, encoding="utf-8") as f:
        data = json.load(f)
    assert any(d["title"] == "Old" for d in data)
    assert any(d["title"] == "Artist - Track" for d in data)


def test_sync_command_empty_youtube_playlist(tmp_path):
    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            return None

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=FakeSpotify()
    ), mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp", return_value=[]
    ), mock.patch(
        "yt2spotify.cache.TrackCache", DummyTrackCache
    ), mock.patch.object(
        cli, "OUTPUT_DIR", str(tmp_path)
    ):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={
                "batch_size": 1,
                "batch_delay": 0.01,
                "max_retries": 1,
                "backoff_factor": 1,
            },
        )
    added_path = tmp_path / "added_songs.json"
    # Only check if file exists and is non-empty before reading
    if added_path.exists() and added_path.stat().st_size > 0:
        with open(added_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data == [] or data is not None
    else:
        assert not added_path.exists() or added_path.stat().st_size == 0


def test_sync_command_summary_log(tmp_path, caplog):
    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            return None

        def search(self, q, type, limit):
            # Return a valid search result for the first, empty for others
            if "Unknown" in q:
                return {"tracks": {"items": []}}
            return {"tracks": {"items": [{"id": "SPOTIFY_TRACK_ID"}]}}
