import sys
import pytest
from unittest import mock
from yt2spotify import cli


def test_main_no_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit):
        cli.main()


def test_main_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--help"])
    with pytest.raises(SystemExit):
        cli.main()
    out = capsys.readouterr().out
    assert "usage" in out.lower() or "help" in out.lower()


@mock.patch("yt2spotify.cli.sync_command")
def test_main_sync_command_called(mock_sync_command, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "sync", "yt_url", "playlist_id"])
    cli.main()
    mock_sync_command.assert_called_once()


@mock.patch("yt2spotify.cli.sync_command", side_effect=Exception("fail"))
def test_main_sync_command_error(mock_sync_command, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "sync", "yt_url", "playlist_id"])
    with pytest.raises(Exception):
        cli.main()
    # Optionally check error output
    # err = capsys.readouterr().err


@mock.patch("yt2spotify.cli.sync_command")
def test_main_with_config_file(mock_sync_command, monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("batch_size = 1")
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "sync", "yt_url", "playlist_id", "--config", str(config_path)],
    )
    cli.main()
    mock_sync_command.assert_called_once()
