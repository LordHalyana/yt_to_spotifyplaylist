import sys
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from rich.logging import RichHandler
from rich.console import Console
from yt2spotify.core import get_spotify_client, async_search_with_cache
from yt2spotify.spotify_utils import spotify_search
from yt2spotify.yt_utils import get_yt_playlist_titles_yt_dlp
from yt2spotify.youtube import get_yt_playlist_titles_api as yt_api_fetch
from yt2spotify.utils import clean_title, parse_artist_track
from yt2spotify.cache import TrackCache
from tqdm import tqdm
import argparse
import toml
import os

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

def sync_command(
    yt_url,
    playlist_id,
    dry_run=False,
    no_progress=False,
    verbose=False,
    yt_api=None,
    progress_wrapper=None,
    config=None
):
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
    # Fetch YouTube playlist titles
    if yt_api:
        titles = yt_api_fetch(yt_api, yt_url)
    else:
        titles = get_yt_playlist_titles_yt_dlp(yt_url)
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
    for idx, (title, (artist, track, track_id)) in iterator:
        if verbose:
            tqdm.write(f"[{idx}] {artist} - {track} => {track_id}") if not no_progress else logger.debug(f"[{idx}] {artist} - {track} => {track_id}")
        if track_id and not dry_run:
            sp.playlist_add_items(playlist_id, [track_id])
            added_count += 1
        elif track_id:
            added_count += 1
        elif verbose:
            tqdm.write(f"  Not found: {title}") if not no_progress else logger.debug(f"  Not found: {title}")
    msg = f"Finished. {added_count} tracks added to Spotify playlist {playlist_id}."
    tqdm.write(msg) if not no_progress else logger.info(msg)

def main():
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
