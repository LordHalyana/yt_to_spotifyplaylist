import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from yt2spotify import matching


def test_is_reasonable_match_jw_and_token_set(monkeypatch):
    # Patch JaroWinkler and token_set_ratio to simulate both paths
    monkeypatch.setattr(matching, "JaroWinkler", None)
    monkeypatch.setattr(matching, "token_set_ratio", None)
    assert matching.is_reasonable_match("A", "B", "A", "B")

    class DummyJW:
        @staticmethod
        def normalized_similarity(a, b):
            return 0.95

    monkeypatch.setattr(matching, "JaroWinkler", DummyJW)
    assert matching.is_reasonable_match("A", "B", "A", "B")

    def dummy_token_set_ratio(a, b):
        return 99

    monkeypatch.setattr(matching, "token_set_ratio", dummy_token_set_ratio)
    assert matching.is_reasonable_match("A", "B", "A", "B")

    # Should fail if artist doesn't match
    assert not matching.is_reasonable_match("A", "B", "X", "B")

    # Should fail if title doesn't match enough
    class DummyJWBad:
        @staticmethod
        def normalized_similarity(a, b):
            return 0.5  # Below threshold

    monkeypatch.setattr(matching, "JaroWinkler", DummyJWBad)
    monkeypatch.setattr(matching, "token_set_ratio", None)
    assert not matching.is_reasonable_match("A", "B", "A", "ZZZ")
