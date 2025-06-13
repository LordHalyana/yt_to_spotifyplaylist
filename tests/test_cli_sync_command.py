from unittest import mock
from yt2spotify import cli

def test_sync_command_dry_run(tmp_path):
    # Mock dependencies
    with mock.patch('yt2spotify.cli.get_spotify_client') as mock_spotify_client, \
         mock.patch('yt2spotify.cli.get_yt_playlist_titles_yt_dlp') as mock_yt_titles, \
         mock.patch('yt2spotify.cli.TrackCache'), \
         mock.patch('yt2spotify.cli.async_search_with_cache') as mock_async_search:
        mock_yt_titles.return_value = ["Artist - Track"]
        mock_spotify = mock.Mock()
        mock_spotify.playlist_tracks.return_value = {"items": [], "next": None}
        mock_spotify_client.return_value = mock_spotify
        mock_async_search.return_value = [("Artist", "Track", "FAKE_TRACK_ID")]
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
                config={"batch_size": 1, "batch_delay": 0.1, "max_retries": 1, "backoff_factor": 1}
            )
            # Check that all_results.json is created
            assert (tmp_path / "all_results.json").exists()
