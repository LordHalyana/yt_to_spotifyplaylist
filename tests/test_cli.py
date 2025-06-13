import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest import mock
from yt2spotify import cli


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
