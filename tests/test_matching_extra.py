from yt2spotify import matching


def test_is_reasonable_match_partial_overlap():
    # Should pass if partial overlap is considered reasonable by the current logic
    assert matching.is_reasonable_match(
        "Daft Punk", "One More Time", "Daft Punk", "Time"
    )


def test_is_reasonable_match_artist_whitespace():
    # Should succeed even with extra whitespace
    assert matching.is_reasonable_match(
        " Daft  Punk ", "One More Time", "Daft Punk", "One More Time"
    )


def test_is_reasonable_match_special_characters():
    # Should succeed with special characters in artist
    assert matching.is_reasonable_match(
        "Daft-Punk", "One More Time", "Daft-Punk", "One More Time"
    )


def test_is_reasonable_match_both_none_algorithms(monkeypatch):
    # Both JaroWinkler and token_set_ratio are None
    monkeypatch.setattr(matching, "JaroWinkler", None)
    monkeypatch.setattr(matching, "token_set_ratio", None)
    assert matching.is_reasonable_match("A", "B", "A", "B")
    # Should fail if title words do not overlap
    assert not matching.is_reasonable_match("A", "B", "A", "ZZZ")
