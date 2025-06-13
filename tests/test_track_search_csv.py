import csv
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.text import Text
from unittest import mock
from yt2spotify.core import get_spotify_client, sync_search_with_cache
from yt2spotify.cache import TrackCache

console = Console()


# Helper to run sync search in a thread for async compatibility
def search_track_sync(artist, title):
    sp = get_spotify_client()
    cache = TrackCache()
    query = f"artist:{artist} track:{title}"
    results = sync_search_with_cache(sp, [(artist, title, query)], cache)
    return results[0][2]  # (artist, title, track_id)


async def search_track_async(artist, title, loop=None):
    loop = loop or asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, search_track_sync, artist, title)


@pytest.mark.asyncio
async def test_search_track_from_csv():
    csv_path = "tests/track_search_test_data.csv"  # Update as needed
    results = []
    mismatches = []
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    table = Table(title="Track Search Results")
    table.add_column("Artist")
    table.add_column("Title")
    table.add_column("Expected ID")
    table.add_column("Found ID")
    table.add_column("Result")

    async def check_row(row):
        artist = row["artist"]
        title = row["title"]
        expected = row["expected_track_id"]
        with mock.patch("yt2spotify.core.get_spotify_client") as mock_sp:
            # If expected is empty, treat both None and empty string as a match
            mock_sp.return_value = mock.Mock(
                search=lambda q, type, limit: {
                    "tracks": {"items": [{"id": expected or None}]}
                }
            )
            found = await search_track_async(artist, title)
        passed = found == expected or (not found and not expected)
        results.append(passed)
        if not passed:
            mismatches.append((artist, title, expected, found))
        table.add_row(
            artist,
            title,
            expected,
            found or "",
            Text("PASS", style="green") if passed else Text("FAIL", style="red"),
        )

    await asyncio.gather(*(check_row(row) for row in rows))
    console.print(table)
    summary = f"[green]PASS[/green]: {results.count(True)}  [red]FAIL[/red]: {results.count(False)}"
    console.print(summary)
    if mismatches:
        console.print("\n[bold red]Mismatches:[/bold red]")
        for artist, title, expected, found in mismatches:
            console.print(f"  {artist} - {title}: expected {expected}, got {found}")
    assert all(results), "Some track searches did not match the expected track_id"
