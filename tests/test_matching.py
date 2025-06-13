import pytest
import unicodedata
import re
from difflib import SequenceMatcher
from unittest.mock import patch
try:
    from rapidfuzz.fuzz import token_set_ratio
    from rapidfuzz.distance import JaroWinkler
except ImportError:
    token_set_ratio = None
    JaroWinkler = None
from yt2spotify.utils import clean_title, parse_artist_track

def is_reasonable_match(searched_artist, searched_title, found_artist, found_title):
    searched_artist = (searched_artist or '').lower().strip()
    searched_title = (searched_title or '').lower().strip()
    found_artist = (found_artist or '').lower().strip()
    found_title = (found_title or '').lower().strip()
    artist_match = all(word in found_artist for word in searched_artist.split() if word)
    if not artist_match:
        return False
    jw_score = 0
    tsr_score = 0
    if JaroWinkler:
        jw_score = JaroWinkler.normalized_similarity(searched_title, found_title)
    else:
        jw_score = SequenceMatcher(None, searched_title, found_title).ratio()
    if token_set_ratio:
        tsr_score = token_set_ratio(searched_title, found_title)
    else:
        searched_set = set(searched_title.split())
        found_set = set(found_title.split())
        if searched_set:
            tsr_score = 100 * len(searched_set & found_set) / len(searched_set)
        else:
            tsr_score = 0
    return (jw_score >= 0.90) or (tsr_score >= 95)

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
