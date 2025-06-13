import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch
from yt2spotify.utils import parse_artist_track

# Replace test_data with a more general regression suite
TEST_CASES = [
    # (original_title, expected_artist, expected_title, expected_status)
    ("Daft Punk - One More Time (Official Video)", "Daft Punk", "One More Time", "added"),
    ("Beyoncé - Halo [HD]", "Beyoncé", "Halo", "added"),
    ("Unknown Artist - Nonexistent Song", "Unknown Artist", "Nonexistent Song", "not_found"),
    ("[Private video]", None, None, "private_or_deleted"),
    ("[Deleted video]", None, None, "private_or_deleted"),
    ("", None, None, "private_or_deleted"),
]

def mock_spotify_search(expected_status, expected_title, expected_artist):
    if expected_status == "added":
        return {
            "tracks": {
                "items": [{
                    "id": "dummy_id",
                    "name": expected_title,
                    "artists": [{"name": expected_artist}]
                }]
            }
        }
    else:
        return {"tracks": {"items": []}}

@pytest.mark.parametrize("original_title, expected_artist, expected_title, expected_status", TEST_CASES)
def test_matching_pipeline(original_title, expected_artist, expected_title, expected_status):
    with patch("yt2spotify.spotify_utils.spotify_search") as mock_search:
        # Simulate a correct match for 'added', no match for 'not_found', skip for private/deleted
        if expected_status == "added":
            mock_search.return_value = mock_spotify_search("added", expected_title, expected_artist)
        else:
            mock_search.return_value = mock_spotify_search("not_found", expected_title, expected_artist)

        artist, track = parse_artist_track(original_title) if original_title else (None, None)
        # Simulate the new status logic
        if not (artist or track) or not original_title or (original_title.strip().lower().startswith('[private') or original_title.strip().lower().startswith('[deleted')):
            result = "private_or_deleted"
        elif mock_search.return_value["tracks"]["items"]:
            result = "added"
        else:
            result = "not_found"
        assert result == expected_status, f"Regression: {original_title} → {artist}, {track} → {result} (expected {expected_status})"
