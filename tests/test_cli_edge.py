import pytest
from unittest import mock
from yt2spotify import cli


def test_load_config_missing_file(tmp_path):
    missing_path = tmp_path / "nonexistent.toml"
    with pytest.raises(FileNotFoundError):
        cli.load_config(str(missing_path))


def test_load_config_invalid_toml(tmp_path):
    bad_path = tmp_path / "bad.toml"
    bad_path.write_text("not a toml file: [unclosed")
    with pytest.raises(Exception):
        cli.load_config(str(bad_path))


def test_sync_command_dry_run(tmp_path):
    class DummySpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            raise AssertionError("Should not be called in dry_run")

        def search(self, q, type, limit):
            return {"tracks": {"items": [{"id": "X"}]}}

    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=DummySpotify()
    ), mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp", return_value=["Artist - Track"]
    ), mock.patch(
        "yt2spotify.cache.TrackCache",
        lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None),
    ), mock.patch.object(
        cli, "OUTPUT_DIR", str(tmp_path)
    ):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=True,
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
    # Should write dryrun_added.json
    dryrun_path = tmp_path / "dryrun_temp" / "dryrun_added.json"
    assert dryrun_path.exists()


def test_sync_command_private_deleted_titles(tmp_path):
    class DummySpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            return None

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    titles = ["[Private video]", "[Deleted video]", " ", "Artist - Track"]
    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=DummySpotify()
    ), mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp", return_value=titles
    ), mock.patch(
        "yt2spotify.cache.TrackCache",
        lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None),
    ), mock.patch.object(
        cli, "OUTPUT_DIR", str(tmp_path)
    ):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=True,
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
    not_found_path = tmp_path / "not_found_songs.json"
    assert not_found_path.exists()
    with open(not_found_path, encoding="utf-8") as f:
        data = f.read()
    # Accept both empty and non-empty files for private/deleted-only cases
    assert data == "[]" or "private_or_deleted" in data


def test_safe_str():
    assert cli.safe_str(None) == ""
    assert cli.safe_str(123) == "123"
    assert cli.safe_str("abc") == "abc"
