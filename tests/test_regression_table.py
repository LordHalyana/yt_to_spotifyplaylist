import pytest

# Historic green/yellow/red table data (replace with actual data from attachment)
test_cases = [
    # Example: (searched_artist, searched_title, expected_found_artist, expected_found_title)
    ("Artist1", "Song1", "Artist1", "Song1"),
    ("Artist2", "Song2", "Artist2", "Song2"),
    # ... add all rows from the table here ...
]


@pytest.mark.parametrize(
    "searched_artist, searched_title, expected_found_artist, expected_found_title",
    test_cases,
)
def test_regression_table(
    searched_artist, searched_title, expected_found_artist, expected_found_title
):
    # Simulate the matching/search logic (replace with actual function call)
    found_artist, found_title, status = run_matching(searched_artist, searched_title)
    assert (
        status == "Correct"
    ), f"Expected status 'Correct' for {searched_artist} - {searched_title}, got {status}"
    assert found_artist == expected_found_artist
    assert found_title == expected_found_title


def run_matching(searched_artist, searched_title):
    # TODO: Replace with actual matching logic or import from yt2spotify
    # This is a placeholder for demonstration
    return searched_artist, searched_title, "Correct"
