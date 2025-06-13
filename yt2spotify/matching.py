from difflib import SequenceMatcher
from typing import Optional, Callable, Any

token_set_ratio: Optional[Callable[[str, str], float]]
JaroWinkler: Optional[Any]

try:
    from rapidfuzz.fuzz import token_set_ratio as _token_set_ratio

    token_set_ratio = _token_set_ratio
except ImportError:
    token_set_ratio = None

try:
    from rapidfuzz.distance import JaroWinkler as _JaroWinkler

    JaroWinkler = _JaroWinkler
except ImportError:
    JaroWinkler = None

__all__ = ["is_reasonable_match"]


def is_reasonable_match(
    searched_artist: Optional[str],
    searched_title: Optional[str],
    found_artist: Optional[str],
    found_title: Optional[str],
) -> bool:
    """
    Determines if a found track is a reasonable match for a searched artist/title.

    Args:
        searched_artist: The artist being searched for.
        searched_title: The title being searched for.
        found_artist: The artist found in the result.
        found_title: The title found in the result.

    Returns:
        True if the match is reasonable, False otherwise.
    """
    searched_artist = (searched_artist or "").lower().strip()
    searched_title = (searched_title or "").lower().strip()
    found_artist = (found_artist or "").lower().strip()
    found_title = (found_title or "").lower().strip()
    artist_match = all(word in found_artist for word in searched_artist.split() if word)
    if not artist_match:
        return False
    jw_score = 0.0
    tsr_score = 0.0
    if JaroWinkler:
        jw_score = JaroWinkler.normalized_similarity(searched_title, found_title)
    else:
        jw_score = SequenceMatcher(None, searched_title, found_title).ratio()
    if token_set_ratio is not None:
        tsr_score = token_set_ratio(searched_title, found_title)
    else:
        searched_set = set(searched_title.split())
        found_set = set(found_title.split())
        if searched_set:
            tsr_score = 100 * len(searched_set & found_set) / len(searched_set)
        else:
            tsr_score = 0.0
    return (jw_score >= 0.90) or (tsr_score >= 95)
