import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest import mock
from yt2spotify import cli

def test_sync_command_already_in_playlist(monkeypatch, tmp_path):
    # Simulate a YouTube title that matches a Spotify track already in playlist
    monkeypatch.setattr(cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["Daft Punk - One More Time"])
    mock_sp = mock.Mock()
    mock_sp.playlist_tracks.return_value = {"items": [{"track": {"id": "TRACK_ID_1"}}], "next": None}
    monkeypatch.setattr(cli, "get_spotify_client", lambda: mock_sp)
    monkeypatch.setattr(cli, "TrackCache", lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None))
    async def fake_async_search_with_cache(sp, queries, cache):
        return [("Daft Punk", "One More Time", "TRACK_ID_1")]
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
    # Check that all_results.json is created and contains the already_in_playlist song (track is lowercased)
    all_results_path = tmp_path / "all_results.json"
    assert all_results_path.exists()
    import json
    with open(all_results_path, encoding="utf-8") as f:
        data = json.load(f)
    print("all_results.json (already_in_playlist):", data)
    assert any((d.get("track") == "one more time" and d.get("status") == "already_in_playlist") for d in data)

# def test_sync_command_added_song(monkeypatch, tmp_path):
#     # Simulate a YouTube title that matches a Spotify track
#     monkeypatch.setattr(cli, "get_yt_playlist_titles_yt_dlp", lambda url: ["Daft Punk - One More Time"])
#     mock_sp = mock.Mock()
#     mock_sp.playlist_tracks.return_value = {"items": [], "next": None}
#     monkeypatch.setattr(cli, "get_spotify_client", lambda: mock_sp)
#     monkeypatch.setattr(cli, "TrackCache", lambda: mock.Mock(get=lambda a, t: None, set=lambda a, t, i: None))
#     async def fake_async_search_with_cache(sp, queries, cache):
#         return [("Daft Punk", "One More Time", "TRACK_ID_1")]
#     monkeypatch.setattr(cli, "async_search_with_cache", fake_async_search_with_cache)
#     monkeypatch.setattr(cli, "OUTPUT_DIR", str(tmp_path))
#     cli.sync_command(
#         yt_url="fake_url",
#         playlist_id="fake_playlist",
#         dry_run=True,
#         no_progress=True,
#         verbose=False,
#         yt_api=None,
#         progress_wrapper=None,
#         config={"batch_size": 1, "batch_delay": 0.1, "max_retries": 1, "backoff_factor": 1}
#     )
#     # Check that all_results.json is created and contains the added song with status 'added' or 'already_in_playlist'
#     all_results_path = tmp_path / "all_results.json"
#     assert all_results_path.exists()
#     import json
#     with open(all_results_path, encoding="utf-8") as f:
#         data = json.load(f)
#     print("all_results.json (added):", data)
#     assert any((d.get("track") == "One More Time" and d.get("status") in ("added", "already_in_playlist")) for d in data)
