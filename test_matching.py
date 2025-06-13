import pytest
import re
from difflib import SequenceMatcher
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

# Example table (replace with your real table rows)
test_data = [
    # (original_title, searched_artist, searched_title, found_artist, found_title, expected_status)
    ("Lil Durk - Think You Glowed (Official Audio)", "Lil Durk", "Think You Glowed (Official Audio)", "Lil Durk", "Think You Glowed", "Correct"),
    ("Lil Durk - Shaking When I Pray (Official Audio)", "Lil Durk", "Shaking When I Pray (Official Audio)", "Lil Durk", "Shaking When I Pray", "Correct"),
    # ... add all rows from your table here ...
]

@pytest.mark.parametrize("original_title, searched_artist, searched_title, found_artist, found_title, expected_status", test_data)
def test_matching_logic(original_title, searched_artist, searched_title, found_artist, found_title, expected_status):
    # Simulate parse_artist_track and matching logic
    artist, track = parse_artist_track(original_title)
    # Simulate a found result (in real test, this would come from Spotify API)
    status = "Correct" if is_reasonable_match(artist, track, found_artist, found_title) else "Mismatch"
    assert status == expected_status, f"{original_title}: expected {expected_status}, got {status}"
