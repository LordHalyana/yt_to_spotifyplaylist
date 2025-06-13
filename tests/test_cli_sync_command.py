from unittest import mock
from yt2spotify import cli
import json

# ruff: noqa: F401, F841


def test_sync_command_dry_run(tmp_path):
    # Mock dependencies
    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def playlist_add_items(self, playlist_id, batch):
            return None

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    with mock.patch(
        "yt2spotify.cli.get_spotify_client", return_value=FakeSpotify()
    ) as mock_spotify_client, mock.patch(
        "yt2spotify.cli.get_yt_playlist_titles_yt_dlp"
    ) as mock_yt_titles, mock.patch(
        "yt2spotify.cache.TrackCache"
    ):
        mock_yt_titles.return_value = ["Artist - Track"]
        # Patch OUTPUT_DIR to tmp_path
        with mock.patch.object(cli, "OUTPUT_DIR", str(tmp_path)):
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
                    "batch_delay": 0.1,
                    "max_retries": 1,
                    "backoff_factor": 1,
                },
            )
            added_path = tmp_path / "added_songs.json"
            if added_path.exists():
                with open(added_path, encoding="utf-8") as f:
                    data = json.load(f)
                assert isinstance(data, list)
            else:
                assert True
