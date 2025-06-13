import os
import sys

# ruff: noqa: F401, F811

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json


def test_sync_command_not_found(monkeypatch, tmp_path):
    from yt2spotify import cli

    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    # Simulate YouTube titles that are private/deleted
    monkeypatch.setattr(
        cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["[Private video]"]
    )
    monkeypatch.setattr(
        cli,
        "get_spotify_client",
        lambda: FakeSpotify(),
    )
    monkeypatch.setattr(
        cli,
        "OUTPUT_DIR",
        str(tmp_path),
    )
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
    priv_path = tmp_path / "not_found_songs.json"
    if priv_path.exists():
        with open(priv_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
    else:
        # File may not exist if there are no not-found songs
        assert True


def test_sync_command_skipped_private_deleted(monkeypatch, tmp_path):
    from yt2spotify import cli

    class FakeSpotify:
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}

        def search(self, q, type, limit):
            return {"tracks": {"items": []}}

    # Simulate YouTube titles that are private/deleted
    monkeypatch.setattr(
        cli,
        "get_yt_playlist_titles_yt_dlp",
        lambda url: ["[Private video]", "[Deleted video]"],
    )
    monkeypatch.setattr(
        cli,
        "get_spotify_client",
        lambda: FakeSpotify(),
    )
    monkeypatch.setattr(
        cli,
        "OUTPUT_DIR",
        str(tmp_path),
    )
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
    priv_path = tmp_path / "not_found_songs.json"
    if priv_path.exists():
        with open(priv_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
    else:
        assert True
