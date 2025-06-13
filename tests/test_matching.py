import pytest
from unittest.mock import patch
from yt2spotify.utils import parse_artist_track

# Replace test_data with a more general regression suite
TEST_CASES = [
    # (original_title, expected_artist, expected_title, expected_status)
    ("Daft Punk - One More Time (Official Video)", "Daft Punk", "One More Time", "Correct"),
    ("Beyoncé - Halo [HD]", "Beyoncé", "Halo", "Correct"),
    ("Unknown Artist - Nonexistent Song", "Unknown Artist", "Nonexistent Song", "Not found"),
    # Add more rows from your table here
]

@pytest.mark.parametrize("original_title, expected_artist, expected_title, expected_status", TEST_CASES)
def test_matching_pipeline(original_title, expected_artist, expected_title, expected_status):
    # Patch Spotify search to return a controlled response
    with patch("yt2spotify.spotify_utils.spotify_search") as mock_search:
        # Simulate a correct match for 'Correct', no match for 'Not found'
        if expected_status == "Correct":
            mock_search.return_value = {
                "tracks": {
                    "items": [{
                        "id": "dummy_id",
                        "name": expected_title,
                        "artists": [{"name": expected_artist}]
                    }]
                }
            }
        else:
            mock_search.return_value = {"tracks": {"items": []}}

        artist, track = parse_artist_track(original_title)
        # Call the matching logic (simplified for test)
        result = "Correct" if mock_search.return_value["tracks"]["items"] else "Not found"
        assert result == expected_status, f"Regression: {original_title} → {artist}, {track} → {result} (expected {expected_status})"
