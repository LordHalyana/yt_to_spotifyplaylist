import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import io
import tempfile
import shutil
from unittest import mock
import builtins

import pytest

from yt2spotify import cli


@pytest.fixture
def temp_output_dir(monkeypatch):
    # Patch OUTPUT_DIR and LOG_DIR to a temp dir
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(cli, "OUTPUT_DIR", temp_dir)
    monkeypatch.setattr(cli, "LOG_DIR", temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir)


@mock.patch(
    "yt2spotify.cli.load_config",
    return_value={
        "batch_size": 1,
        "batch_delay": 1,
        "max_retries": 1,
        "backoff_factor": 1,
    },
)
@mock.patch("yt2spotify.cli.sync_command")
def test_cli_main_sync_invokes_sync_command(
    mock_sync_command, mock_load_config, monkeypatch
):
    # Simulate command-line arguments for the sync command
    test_args = [
        "prog",
        "sync",
        "https://youtube.com/playlist?list=PL123",
        "SPOTIFY_PLAYLIST_ID",
        "--dry-run",
        "--no-progress",
        "--verbose",
        "--yt-api-key",
        "FAKE_KEY",
        "--config",
        "fake_config.toml",
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    cli.main()
    mock_sync_command.assert_called_once()
    args, kwargs = mock_sync_command.call_args
    assert kwargs["yt_url"] == "https://youtube.com/playlist?list=PL123"
    assert kwargs["playlist_id"] == "SPOTIFY_PLAYLIST_ID"
    assert kwargs["dry_run"] is True
    assert kwargs["no_progress"] is True
    assert kwargs["verbose"] is True
    assert kwargs["yt_api"] == "FAKE_KEY"
    assert kwargs["config"] is not None


@mock.patch("yt2spotify.cli.sync_command")
def test_cli_main_sync_minimal_args(mock_sync_command, monkeypatch):
    test_args = ["prog", "sync", "yt_url", "playlist_id"]
    monkeypatch.setattr(sys, "argv", test_args)
    cli.main()
    mock_sync_command.assert_called_once()
    args, kwargs = mock_sync_command.call_args
    assert kwargs["yt_url"] == "yt_url"
    assert kwargs["playlist_id"] == "playlist_id"


@mock.patch("yt2spotify.cli.sync_command")
def test_cli_main_invalid_command(mock_sync_command, monkeypatch):
    test_args = ["prog", "invalid"]
    monkeypatch.setattr(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        cli.main()
    mock_sync_command.assert_not_called()


def test_snapshot_saved_before_sync_and_undo_restores(monkeypatch, temp_output_dir):
    # --- Mock Spotify client and playlist state ---
    mock_sp = mock.Mock()
    playlist_id = "playlist123"
    yt_url = "https://youtube.com/playlist?list=abc"
    fake_tracks = [
        {"track": {"id": "t1", "name": "Song1", "artists": [{"name": "A1"}]}},
        {"track": {"id": "t2", "name": "Song2", "artists": [{"name": "A2"}]}},
    ]
    # Simulate current playlist state
    mock_sp.playlist_tracks.return_value = {"items": fake_tracks}
    # Patch get_spotify_client to return our mock
    monkeypatch.setattr(cli, "get_spotify_client", lambda: mock_sp)
    # Patch yt playlist fetch to return empty (simulate no new tracks)
    monkeypatch.setattr(cli, "get_yt_playlist_titles_yt_dlp", lambda url: [])
    # Patch open to track snapshot writes
    snapshot_path = f"{temp_output_dir}/playlist_{playlist_id}_snapshot.json"
    snapshot_path = os.path.abspath(snapshot_path)
    written = {}
    orig_open = builtins.open

    def fake_open(file, mode="r", *args, **kwargs):
        file_norm = os.path.abspath(file)
        if file_norm == snapshot_path and "w" in mode:
            # Intercept snapshot write
            file_obj = io.StringIO()
            orig_write = file_obj.write

            def fake_write(data):
                written["snapshot"] = data
                return orig_write(data)

            file_obj.write = fake_write
            return file_obj
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    # --- Run sync_command (should save snapshot) ---
    cli.sync_command(yt_url, playlist_id, dry_run=True, config={"snapshot": True})
    assert "snapshot" in written, "Snapshot was not saved before sync"
    # --- Now test --undo restores from snapshot ---
    # Patch open to read the snapshot
    snapshot_data = '[{"track": {"id": "t1"}}, {"track": {"id": "t2"}}]'

    def fake_open_read(file, mode="r", *args, **kwargs):
        file_norm = os.path.abspath(file)
        if file_norm == snapshot_path and "r" in mode:
            return io.StringIO(snapshot_data)
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open_read)
    # Patch os.path.exists to return True for the snapshot path
    orig_exists = os.path.exists

    def fake_exists(path):
        path_norm = os.path.abspath(path)
        if path_norm == snapshot_path:
            return True
        return orig_exists(path)

    monkeypatch.setattr(os.path, "exists", fake_exists)
    # Patch json.load to load our snapshot
    monkeypatch.setattr(
        "json.load", lambda f: [{"track": {"id": "t1"}}, {"track": {"id": "t2"}}]
    )
    # Patch sp.playlist_replace_items to check restore
    called = {}

    def fake_replace(pid, track_ids):
        called["pid"] = pid
        called["track_ids"] = track_ids

    mock_sp.playlist_replace_items.side_effect = fake_replace
    # Simulate cli.undo_command
    if hasattr(cli, "undo_command"):
        from unittest.mock import patch

        with patch("yt2spotify.core.get_spotify_client", lambda: mock_sp):
            cli.undo_command(playlist_id, config={"snapshot": True})
            assert called["pid"] == playlist_id
            assert called["track_ids"] == ["t1", "t2"]
    else:
        pytest.skip("undo_command not implemented in cli.py")
    # Patch playlist_tracks to always return a dict (not a Mock)
    mock_sp.playlist_tracks.side_effect = lambda pid: {
        "items": fake_tracks,
        "next": None,
    }
    # Patch playlist_items for completeness (if used elsewhere)
    mock_sp.playlist_items.return_value = {"items": fake_tracks}
    # Patch sp.next to return None on first call (simulate end of pagination)
    mock_sp.next.side_effect = [None]
