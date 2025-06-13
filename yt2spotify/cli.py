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
    # 1. Gather all YouTube titles and filter out private/deleted
    print("## Working on Youtube Titles ##")
    if yt_api:
        titles = yt_api_fetch(yt_api, yt_url)
    else:
        titles = get_yt_playlist_titles_yt_dlp(yt_url)
    print("## Compiled Youtube Titles ##")

    # Parse and filter YouTube titles
    parsed = []
    skipped_songs = []
    for title in titles:
        artist, track = parse_artist_track(title)
        if not (artist or track) or not title or title.strip().lower().startswith('[private') or title.strip().lower().startswith('[deleted'):
            skipped_songs.append({"title": title, "artist": artist, "track": track, "status": "private_or_deleted"})
        else:
            parsed.append((title, artist, track))
    # Write skipped to output immediately
    with open(NOT_FOUND_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(skipped_songs, f, ensure_ascii=False, indent=2)

    # Get all track IDs in the Spotify playlist (avoid duplicates)
    sp = get_spotify_client()
    playlist_tracks = set()
    results = sp.playlist_tracks(playlist_id)
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                playlist_tracks.add(track["id"])
        results = sp.next(results) if results.get("next") else None

    # Prepare queries for only non-private/deleted
    queries = []
    for title, artist, track in parsed:
        query = f"artist:{artist} track:{track}" if artist else clean_title(title)
        queries.append((artist or '', track or '', query.strip(), title))

    # Async search with cache (only for tracks not already in playlist)
    cache = TrackCache()
    search_queries = [(a, t, q) for a, t, q, _ in queries]
    loop = asyncio.get_event_loop()
    search_results = loop.run_until_complete(async_search_with_cache(sp, search_queries, cache))

    # Get batch size and delay from config or use defaults
    batch_size = int(config.get("batch_size", 25))
    batch_delay = float(config.get("batch_delay", 2.0))
    max_retries = int(config.get("max_retries", 5))
    backoff_factor = float(config.get("backoff_factor", 2.0))

    # Build a set of track IDs already in the playlist for deduplication
    added_count = 0
    batch = []
    added_songs = []
    not_found_songs = []
    for (artist, track, query, title), (_, _, track_id) in zip(queries, search_results):
        if track_id and track_id in playlist_tracks:
            # Already in playlist, skip adding
            added_songs.append({"title": title, "artist": artist, "track": track, "track_id": track_id, "status": "already_in_playlist"})
            continue
        if track_id and not dry_run:
            batch.append(track_id)
            added_songs.append({"title": title, "artist": artist, "track": track, "track_id": track_id, "status": "added"})
            if len(batch) == batch_size:
                # Robust Spotify add with rate limit handling
                retries = 0
                while True:
                    try:
                        sp.playlist_add_items(playlist_id, batch)
                        break
                    except Exception as e:
                        # Try to extract Retry-After from exception (spotipy uses requests)
                        retry_after = None
                        if hasattr(e, 'headers') and hasattr(getattr(e, 'headers'), 'get'):
                            retry_after = getattr(e, 'headers').get('Retry-After')
                        if hasattr(e, 'http_status') and getattr(e, 'http_status') == 429:
                            if retry_after is not None:
                                try:
                                    wait = float(retry_after)
                                except Exception:
                                    wait = batch_delay * (backoff_factor ** retries)
                            else:
                                wait = batch_delay * (backoff_factor ** retries)
                            logger.warning(f"Spotify rate limit hit. Retrying after {wait:.1f}s (retry {retries+1}/{max_retries})...")
                            import time; time.sleep(wait)
                            retries += 1
                            if retries >= max_retries:
                                logger.error("Max retries reached for Spotify rate limit. Skipping batch.")
                                break
                        else:
                            logger.error(f"Spotify API error: {e}")
                            break
                batch.clear()
                import time; time.sleep(batch_delay)
            added_count += 1
        elif track_id:
            added_songs.append({"title": title, "artist": artist, "track": track, "track_id": track_id, "status": "already_in_playlist"})
        else:
            not_found_songs.append({"title": title, "artist": artist, "track": track, "status": "not_found"})
    if batch and not dry_run:
        retries = 0
        while True:
            try:
                sp.playlist_add_items(playlist_id, batch)
                break
            except Exception as e:
                retry_after = None
                if hasattr(e, 'headers') and hasattr(getattr(e, 'headers'), 'get'):
                    retry_after = getattr(e, 'headers').get('Retry-After')
                if hasattr(e, 'http_status') and getattr(e, 'http_status') == 429:
                    if retry_after is not None:
                        try:
                            wait = float(retry_after)
                        except Exception:
                            wait = batch_delay * (backoff_factor ** retries)
                    else:
                        wait = batch_delay * (backoff_factor ** retries)
                    logger.warning(f"Spotify rate limit hit. Retrying after {wait:.1f}s (retry {retries+1}/{max_retries})...")
                    import time; time.sleep(wait)
                    retries += 1
                    if retries >= max_retries:
                        logger.error("Max retries reached for Spotify rate limit. Skipping batch.")
                        break
                else:
                    logger.error(f"Spotify API error: {e}")
                    break
        import time; time.sleep(batch_delay)

    # Merge skipped and not found for output
    with open(NOT_FOUND_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(not_found_songs + skipped_songs, f, ensure_ascii=False, indent=2)

    deleted_count = len(skipped_songs)
    missing_count = len(not_found_songs)
    msg = (
        f"Finished.\n"
        f"{added_count} tracks added to Spotify playlist {playlist_id}.\n"
        f"{deleted_count} tracks were deleted/private on YouTube.\n"
        f"{missing_count} tracks were missing on Spotify."
    )
    tqdm.write(msg) if not no_progress else logger.info(msg)
    with open(ADDED_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(added_songs, f, ensure_ascii=False, indent=2)
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
