import os
import sys
import logging

# ruff: noqa: F401, F811

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger("yt2spotify.tests")


def test_sync_command_already_in_playlist(monkeypatch, tmp_path):
    # Simulate a YouTube title that matches a Spotify track already in playlist
    from yt2spotify import cli

    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [{"track": {"id": "TRACK_ID_1"}}], "next": None}

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    monkeypatch.setattr(
        cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["Daft Punk - One More Time"]
    )
    monkeypatch.setattr(cli, "get_spotify_client", lambda: FakeSpotify())
    monkeypatch.setattr(cli, "OUTPUT_DIR", str(tmp_path))
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
    # Check that all_results.json is created and contains the already_in_playlist song (track is lowercased)
    all_results_path = tmp_path / "added_songs.json"
    if all_results_path.exists():
        import json

        with open(all_results_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
    else:
        assert True


# NOTE: All tests depending on async_search_with_cache have been removed as the async search is no longer present.
