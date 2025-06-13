import json
from unittest import mock
from yt2spotify import cli

# 1. Spotify API Error Handling (429, retries, max_retries)
def test_sync_command_spotify_429_retry(tmp_path):
    class FakeSpotify:
        class Fake429(Exception):
            def __init__(self):
                self.http_status = 429
                self.headers = mock.Mock()
                self.headers.get = lambda k: "1" if k == "Retry-After" else None
        def __init__(self):
            self.calls = 0
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}
        def playlist_add_items(self, playlist_id, batch):
            self.calls += 1
            print(f"playlist_add_items call #{self.calls}")
            if self.calls < 3:
                raise FakeSpotify.Fake429()
            return None
    added_path = tmp_path / "added_songs.json"
    with mock.patch('yt2spotify.cli.get_spotify_client', return_value=FakeSpotify()) as m_spotify, \
         mock.patch('yt2spotify.cli.get_yt_playlist_titles_yt_dlp', return_value=["Artist - Track"]), \
         mock.patch('yt2spotify.cli.TrackCache'), \
         mock.patch('yt2spotify.cli.async_search_with_cache', return_value=[("Artist", "Track", "FAKE_TRACK_ID")]), \
         mock.patch.object(cli, "OUTPUT_DIR", str(tmp_path)), \
         mock.patch.object(cli, "ADDED_SONGS_PATH", str(added_path)), \
         mock.patch("time.sleep", return_value=None):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={"batch_size": 1, "batch_delay": 0.01, "max_retries": 3, "backoff_factor": 1}
        )
        # Debug: print all files in tmp_path
        print("Files in tmp_path:", list(tmp_path.iterdir()))
        # Debug: print calls
        print("playlist_add_items calls:", m_spotify.return_value.calls)
        # Assert file exists
        assert added_path.exists(), f"added_songs.json not found in {list(tmp_path.iterdir())}"
        # Optionally, print file contents
        with open(added_path, encoding="utf-8") as f:
            print("added_songs.json contents:", f.read())

# 2. Output File Merging/Appending
def test_sync_command_output_file_merging(tmp_path):
    class FakeSpotify:
        class Fake429(Exception):
            def __init__(self):
                self.http_status = 429
                self.headers = mock.Mock()
                self.headers.get = lambda k: "1" if k == "Retry-After" else None
        def __init__(self):
            self.calls = 0
        def playlist_tracks(self, playlist_id):
            return {"items": [], "next": None}
        def playlist_add_items(self, playlist_id, batch):
            self.calls += 1
            return None
    added_path = tmp_path / "added_songs.json"
    # Pre-populate with an entry
    with open(added_path, "w", encoding="utf-8") as f:
        json.dump([{"title": "Old", "artist": "A", "track": "B", "track_id": "X", "status": "added"}], f)
    with mock.patch('yt2spotify.cli.get_spotify_client', return_value=FakeSpotify()), \
         mock.patch('yt2spotify.cli.get_yt_playlist_titles_yt_dlp', return_value=["Artist - Track"]), \
         mock.patch('yt2spotify.cli.TrackCache'), \
         mock.patch('yt2spotify.cli.async_search_with_cache', return_value=[("Artist", "Track", "FAKE_TRACK_ID")]), \
         mock.patch.object(cli, "OUTPUT_DIR", str(tmp_path)), \
         mock.patch.object(cli, "ADDED_SONGS_PATH", str(added_path)):
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={"batch_size": 1, "batch_delay": 0.01, "max_retries": 1, "backoff_factor": 1}
        )
    # Should have appended, not overwritten
    with open(added_path, encoding="utf-8") as f:
        data = json.load(f)
    print("added_songs.json after merging:", data)
    assert any(d["title"] == "Old" for d in data)
    assert any(d["title"] == "Artist - Track" for d in data)

# 3. Edge Cases in Output Generation
def test_sync_command_empty_youtube_playlist(tmp_path):
    with mock.patch('yt2spotify.cli.get_spotify_client') as mock_spotify_client, \
         mock.patch('yt2spotify.cli.get_yt_playlist_titles_yt_dlp', return_value=[]), \
         mock.patch('yt2spotify.cli.TrackCache'), \
         mock.patch('yt2spotify.cli.async_search_with_cache', return_value=[]), \
         mock.patch.object(cli, "OUTPUT_DIR", str(tmp_path)):
        mock_spotify = mock.Mock()
        mock_spotify.playlist_tracks.return_value = {"items": [], "next": None}
        mock_spotify.playlist_add_items.return_value = None
        mock_spotify_client.return_value = mock_spotify
        cli.sync_command(
            yt_url="fake_url",
            playlist_id="fake_playlist",
            dry_run=False,
            no_progress=True,
            verbose=False,
            yt_api=None,
            progress_wrapper=None,
            config={"batch_size": 1, "batch_delay": 0.01, "max_retries": 1, "backoff_factor": 1}
        )
    # Should not create added_songs.json
    assert not (tmp_path / "added_songs.json").exists()

# 4. Logging and Summary
def test_sync_command_summary_log(tmp_path, caplog):
    with mock.patch('yt2spotify.cli.get_spotify_client') as mock_spotify_client, \
         mock.patch('yt2spotify.cli.get_yt_playlist_titles_yt_dlp', return_value=["Artist - Track", "[Private video]", "Unknown Artist - Unknown Track"]), \
         mock.patch('yt2spotify.cli.TrackCache'), \
         mock.patch('yt2spotify.cli.async_search_with_cache', return_value=[("Artist", "Track", "FAKE_TRACK_ID"), (None, None, None), ("Unknown Artist", "Unknown Track", None)]), \
         mock.patch.object(cli, "OUTPUT_DIR", str(tmp_path)):
        mock_spotify = mock.Mock()
        mock_spotify.playlist_tracks.return_value = {"items": [], "next": None}
        mock_spotify.playlist_add_items.return_value = None
        mock_spotify_client.return_value = mock_spotify
        with caplog.at_level("INFO"):
            cli.sync_command(
                yt_url="fake_url",
                playlist_id="fake_playlist",
                dry_run=False,
                no_progress=True,
                verbose=False,
                yt_api=None,
                progress_wrapper=None,
                config={"batch_size": 1, "batch_delay": 0.01, "max_retries": 1, "backoff_factor": 1}
            )
        # Check summary log
        assert any("tracks added to Spotify playlist" in r.message for r in caplog.records)
        assert any("tracks were already in playlist" in r.message for r in caplog.records)
        assert any("tracks were deleted/private on YouTube" in r.message for r in caplog.records)
        assert any("tracks were missing on Spotify" in r.message for r in caplog.records)

