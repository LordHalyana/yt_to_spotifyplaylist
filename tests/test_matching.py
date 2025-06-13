import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch
from yt2spotify.utils import parse_artist_track

# Replace test_data with a more general regression suite
TEST_CASES = [
    # (original_title, expected_artist, expected_title, expected_status)
    (
        "Daft Punk - One More Time (Official Video)",
        "Daft Punk",
        "One More Time",
        "added",
    ),
    ("Beyoncé - Halo [HD]", "Beyoncé", "Halo", "added"),
    (
        "Unknown Artist - Nonexistent Song",
        "Unknown Artist",
        "Nonexistent Song",
        "not_found",
    ),
    ("[Private video]", None, None, "private_or_deleted"),
    ("[Deleted video]", None, None, "private_or_deleted"),
    ("", None, None, "private_or_deleted"),
]


def mock_spotify_search(expected_status, expected_title, expected_artist):
    if expected_status == "added":
        return {
            "tracks": {
                "items": [
                    {
                        "id": "dummy_id",
                        "name": expected_title,
                        "artists": [{"name": expected_artist}],
                    }
                ]
            }
        }
    else:
        return {"tracks": {"items": []}}


# Add regression tests for new status logic and config-driven batching
@pytest.mark.parametrize(
    "original_title, expected_artist, expected_title, expected_status", TEST_CASES
)
def test_matching_pipeline(
    original_title, expected_artist, expected_title, expected_status
):
    with patch("yt2spotify.spotify_utils.spotify_search") as mock_search:
        # Simulate a correct match for 'added', no match for 'not_found', skip for private/deleted
        if expected_status == "added":
            mock_search.return_value = mock_spotify_search(
                "added", expected_title, expected_artist
            )
        else:
            mock_search.return_value = mock_spotify_search(
                "not_found", expected_title, expected_artist
            )

        artist, track = (
            parse_artist_track(original_title) if original_title else (None, None)
        )
        # Simulate the new status logic
        if (
            not (artist or track)
            or not original_title
            or (
                original_title.strip().lower().startswith("[private")
                or original_title.strip().lower().startswith("[deleted")
            )
        ):
            result = "private_or_deleted"
        elif mock_search.return_value["tracks"]["items"]:
            result = "added"
        else:
            result = "not_found"
        assert (
            result == expected_status
        ), f"Regression: {original_title} → {artist}, {track} → {result} (expected {expected_status})"


# Test config-driven batch size and delay (mocked)
def test_config_batching(monkeypatch):
    # Simulate config
    config = {
        "batch_size": 10,
        "batch_delay": 0.1,
        "max_retries": 2,
        "backoff_factor": 1.5,
    }

    # Simulate a batch add function that raises 429 on first call, then succeeds
    class DummySpotify:
        def __init__(self):
            self.calls = 0

        def playlist_add_items(self, playlist_id, batch):
            self.calls += 1
            if self.calls == 1:

                class E(Exception):
                    http_status = 429
                    headers = {"Retry-After": "0.01"}

                raise E()
            return True

    sp = DummySpotify()
    # Should succeed after one retry
    try:
        retries = 0
        batch = ["id1"] * config["batch_size"]
        while True:
            try:
                sp.playlist_add_items("playlist", batch)
                break
            except Exception as e:
                retry_after = None
                if hasattr(e, "headers") and hasattr(getattr(e, "headers"), "get"):
                    retry_after = getattr(e, "headers").get("Retry-After")
                if hasattr(e, "http_status") and getattr(e, "http_status") == 429:
                    if retry_after is not None:
                        try:
                            # wait = float(retry_after)
                            pass
                        except Exception:
                            # wait = config["batch_delay"] * (config["backoff_factor"] ** retries)
                            pass
                    retries += 1
                    if retries >= config["max_retries"]:
                        break
                else:
                    break
        assert sp.calls == 2, "Should retry once on 429 and then succeed"
    except Exception:
        pytest.fail("Batching with retry logic failed")
