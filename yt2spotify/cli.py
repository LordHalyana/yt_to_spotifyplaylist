import asyncio
import logging
from typing import Any, Dict, Optional
from rich.logging import RichHandler
from rich.console import Console
from yt2spotify.core import get_spotify_client, async_search_with_cache
from yt2spotify.yt_utils import get_yt_playlist_titles_yt_dlp
from yt2spotify.youtube import get_yt_playlist_titles_api as yt_api_fetch
from yt2spotify.utils import clean_title, parse_artist_track
from yt2spotify.cache import TrackCache
from tqdm import tqdm
import argparse
import toml
import os
import json

console = Console()

# Setup logging with RichHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_time=False, show_level=True, show_path=False)]
)
logger = logging.getLogger("yt2spotify")

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a TOML file. If not provided, load the package default.
    Returns:
        Dictionary of config values.
    """
    if config_path:
        path = config_path
    else:
        # Try both yt2spotify/default_config.toml and default_config.toml for editable installs
        pkg_path = os.path.join(os.path.dirname(__file__), "yt2spotify", "default_config.toml")
        local_path = os.path.join(os.path.dirname(__file__), "default_config.toml")
        path = pkg_path if os.path.exists(pkg_path) else local_path
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)

# Set up output and log directories
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

ADDED_SONGS_PATH = os.path.join(OUTPUT_DIR, "added_songs.json")
NOT_FOUND_SONGS_PATH = os.path.join(OUTPUT_DIR, "not_found_songs.json")
LOG_PATH = os.path.join(LOG_DIR, "run_log.csv")
MISSING_ON_SPOTIFY_PATH = os.path.join(OUTPUT_DIR, "missing_on_spotify.json")

def sync_command(
    yt_url: str,
    playlist_id: str,
    dry_run: bool = False,
    no_progress: bool = False,
    verbose: bool = False,
    yt_api: Optional[str] = None,
    progress_wrapper: Optional[Any] = None,
    config: Optional[dict[str, Any]] = None
) -> None:
    """
    Main sync logic. Accepts config dict for stop-words, thresholds, and backoff.
    """
    if config is None:
        config = load_config(None)
    # Set log level for verbosity
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    print("## Working on Youtube Titles ##")
    # Fetch YouTube playlist titles
    if yt_api:
        titles = yt_api_fetch(yt_api, yt_url)
    else:
        titles = get_yt_playlist_titles_yt_dlp(yt_url)
    print("## Compiled Youtube Titles ##")
    sp = get_spotify_client()
    cache = TrackCache()
    queries = []
    stop_words = set(config.get("stop_words", []))
    for title in titles:
        artist, track = parse_artist_track(title)
        # Remove stop words from query
        query = f"artist:{artist} track:{track}" if artist else clean_title(title)
        for word in stop_words:
            query = query.replace(word, "")
        queries.append((artist or '', track or '', query.strip()))
    # Async search with cache
    loop = asyncio.get_event_loop()
    # Pass thresholds and backoff to async_search_with_cache via config if needed
    results = loop.run_until_complete(async_search_with_cache(sp, queries, cache))
    added_count = 0
    iterator = enumerate(zip(titles, results), 1)
    # Universal progress bar logic
    if progress_wrapper is not None:
        iterator = progress_wrapper(iterator, total=len(titles))
    elif not no_progress:
        iterator = tqdm(iterator, total=len(titles), desc="Syncing", unit="track")
    added_songs = []
    not_found_songs = []
    skipped_songs = []
    for idx, (title, (artist, track, track_id)) in iterator:
        status = None
        # Detect private/deleted/empty
        if not (artist or track) or not title or title.strip().lower().startswith('[private') or title.strip().lower().startswith('[deleted'):
            status = "private_or_deleted"
            skipped_songs.append({"title": title, "artist": artist, "track": track, "status": status})
            if verbose:
                tqdm.write(f"  Skipped (private/deleted): {title}") if not no_progress else logger.debug(f"  Skipped (private/deleted): {title}")
            continue
        if track_id and not dry_run:
            sp.playlist_add_items(playlist_id, [track_id])
            added_count += 1
            status = "added"
            added_songs.append({"title": title, "artist": artist, "track": track, "track_id": track_id, "status": status})
        elif track_id:
            added_count += 1
            status = "already_in_playlist"
            added_songs.append({"title": title, "artist": artist, "track": track, "track_id": track_id, "status": status})
        else:
            status = "not_found"
            not_found_songs.append({"title": title, "artist": artist, "track": track, "status": status})
            if verbose:
                tqdm.write(f"  Not found: {title}") if not no_progress else logger.debug(f"  Not found: {title}")
    deleted_count = sum(1 for s in not_found_songs + skipped_songs if s.get("status") == "private_or_deleted")
    missing_count = sum(1 for s in not_found_songs if s.get("status") == "not_found")
    msg = (
        f"Finished.\n"
        f"{added_count} tracks added to Spotify playlist {playlist_id}.\n"
        f"{deleted_count} tracks were deleted/private on YouTube.\n"
        f"{missing_count} tracks were missing on Spotify."
    )
    tqdm.write(msg) if not no_progress else logger.info(msg)
    # Write output files
    with open(ADDED_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(added_songs, f, ensure_ascii=False, indent=2)
    with open(NOT_FOUND_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(not_found_songs + skipped_songs, f, ensure_ascii=False, indent=2)
    # Write missing_on_spotify.json: only songs that are not found on Spotify and not private/deleted
    missing_on_spotify = [
        {"title": s["title"], "artist": s["artist"], "track": s["track"], "status": s["status"]}
        for s in not_found_songs if s.get("status") == "not_found"
    ]
    with open(MISSING_ON_SPOTIFY_PATH, "w", encoding="utf-8") as f:
        json.dump(missing_on_spotify, f, ensure_ascii=False, indent=2)

def main() -> None:
    parser = argparse.ArgumentParser(description='Sync YouTube playlist to Spotify playlist')
    subparsers = parser.add_subparsers(dest='command', required=True)
    sync_parser = subparsers.add_parser('sync', help='Sync a YouTube playlist to a Spotify playlist')
    sync_parser.add_argument('yt_url', help='YouTube playlist URL')
    sync_parser.add_argument('playlist_id', help='Spotify playlist ID')
    sync_parser.add_argument('--dry-run', action='store_true', help='Do not add tracks to playlist, just log what would be added')
    sync_parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    sync_parser.add_argument('--verbose', action='store_true', help='Verbose output (sets log level to DEBUG)')
    sync_parser.add_argument('--yt-api-key', help='YouTube Data API v3 key (optional, enables API fallback)')
    sync_parser.add_argument('--config', help='Path to a TOML config file (overrides package default)')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == 'sync':
        sync_command(
            yt_url=args.yt_url,
            playlist_id=args.playlist_id,
            dry_run=args.dry_run,
            no_progress=args.no_progress,
            verbose=args.verbose,
            yt_api=args.yt_api_key,
            progress_wrapper=None,
            config=config
        )

if __name__ == '__main__':
    main()
