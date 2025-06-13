import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest import mock
from yt2spotify import cli

def test_sync_command_not_found(monkeypatch, tmp_path):
    # Simulate YouTube titles that are private/deleted
    monkeypatch.setattr(cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["[Private video]"])
    monkeypatch.setattr(cli, "get_spotify_client", lambda: mock.Mock(playlist_tracks=lambda pid: {"items": [], "next": None}))
    monkeypatch.setattr(cli, "TrackCache", lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None))
    async def fake_async_search_with_cache(sp, queries, cache):
        return []
    monkeypatch.setattr(cli, "async_search_with_cache", fake_async_search_with_cache)
    # Patch OUTPUT_DIR to tmp_path
    monkeypatch.setattr(cli, "OUTPUT_DIR", str(tmp_path))
    cli.sync_command(
        yt_url="fake_url",
        playlist_id="fake_playlist",
        dry_run=True,
        no_progress=True,
        verbose=False,
        yt_api=None,
        progress_wrapper=None,
        config={"batch_size": 1, "batch_delay": 0.1, "max_retries": 1, "backoff_factor": 1}
    )
    # Check that private_deleted_songs.json is created and contains the private video
    priv_path = tmp_path / "private_deleted_songs.json"
    assert priv_path.exists()
    import json
    with open(priv_path, encoding="utf-8") as f:
        data = json.load(f)
    assert any("Private video" in (d.get("title") or "") for d in data)

def test_sync_command_skipped_private_deleted(monkeypatch, tmp_path):
    # Simulate YouTube titles that are private/deleted
    monkeypatch.setattr(cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["[Private video]", "[Deleted video]"])
    monkeypatch.setattr(cli, "get_spotify_client", lambda: mock.Mock(playlist_tracks=lambda pid: {"items": [], "next": None}))
    monkeypatch.setattr(cli, "TrackCache", lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None))
    async def fake_async_search_with_cache(sp, queries, cache):
        return []
    monkeypatch.setattr(cli, "async_search_with_cache", fake_async_search_with_cache)
    monkeypatch.setattr(cli, "OUTPUT_DIR", str(tmp_path))
    cli.sync_command(
        yt_url="fake_url",
        playlist_id="fake_playlist",
        dry_run=True,
        no_progress=True,
        verbose=False,
        yt_api=None,
        progress_wrapper=None,
        config={"batch_size": 1, "batch_delay": 0.1, "max_retries": 1, "backoff_factor": 1}
    )
    # Check that private_deleted_songs.json is created and contains the skipped songs
    priv_path = tmp_path / "private_deleted_songs.json"
    assert priv_path.exists()
    import json
    with open(priv_path, encoding="utf-8") as f:
        data = json.load(f)
    assert any("private_or_deleted" in (d.get("status") or "") for d in data)
