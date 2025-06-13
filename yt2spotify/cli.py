# mypy: disable-error-code=assignment
import logging
from typing import Any, Optional
from yt2spotify.core import get_spotify_client
from yt2spotify.yt_utils import get_yt_playlist_titles_yt_dlp
from yt2spotify.youtube import get_yt_playlist_titles_api as yt_api_fetch
from yt2spotify.utils import clean_title, parse_artist_track
import toml
import os
import json
from yt2spotify.logging_config import logger


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load configuration from a TOML file. If not provided, load the package default.
    Returns:
        Dictionary of config values.
    """
    path: str
    if config_path:
        path = config_path
    else:
        # Try both yt2spotify/default_config.toml and default_config.toml for editable installs
        pkg_path = os.path.join(
            os.path.dirname(__file__), "yt2spotify", "default_config.toml"
        )
        local_path = os.path.join(os.path.dirname(__file__), "default_config.toml")
        path = pkg_path if os.path.exists(pkg_path) else local_path
    config: dict[str, Any] = toml.load(path)
    return config


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
    config: Optional[dict[str, Any]] = None,
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
    logger.info("## Working on Youtube Titles ##")
    if yt_api:
        titles = yt_api_fetch(yt_api, yt_url)
    else:
        titles = get_yt_playlist_titles_yt_dlp(yt_url)
    logger.info("## Compiled Youtube Titles ##")

    # Parse and filter YouTube titles
    parsed = []
    skipped_songs = []
    for title in titles:
        artist, track = parse_artist_track(title)
        if (
            not (artist or track)
            or not title
            or title.strip().lower().startswith("[private")
            or title.strip().lower().startswith("[deleted")
        ):
            skipped_songs.append(
                {
                    "title": title,
                    "artist": artist,
                    "track": track,
                    "status": "private_or_deleted",
                }
            )
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
        queries.append((artist or "", track or "", query.strip(), title))

    # Sync search with cache (only for tracks not already in playlist)
    from yt2spotify.cache import TrackCache

    cache = TrackCache()
    search_results = []
    for artist, track, query, title in queries:
        # Check cache first
        cached_id = cache.get(artist, track)
        if cached_id:
            search_results.append((artist, track, cached_id))
            continue
        # Perform Spotify search (synchronous, single track)
        result = sp.search(q=query, type="track", limit=1) or {}
        items = result.get("tracks", {}).get("items", [])
        if items:
            track_id = items[0]["id"]
            cache.set(artist, track, track_id)
            search_results.append((artist, track, track_id))
        else:
            search_results.append((artist, track, None))

    # Get batch size and delay from config or use defaults
    batch_size = int(config.get("batch_size", 25))
    # Set a high default batch_delay for safety
    batch_delay = float(config.get("batch_delay", 10.0))
    max_retries = int(config.get("max_retries", 5))
    backoff_factor = float(config.get("backoff_factor", 2.0))
    min_retry_after = (
        10.0  # Always wait at least 10 seconds after a 429 if Retry-After is missing
    )

    # Build a set of track IDs already in the playlist for deduplication
    added_count = 0
    batch = []
    added_songs = []
    not_found_songs: list[dict[str, str]] = []
    for (artist, track, query, title), (_, _, track_id) in zip(queries, search_results):
        if track_id and track_id in playlist_tracks:
            # Already in playlist, skip adding
            added_songs.append(
                {
                    "title": title,
                    "artist": artist,
                    "track": track,
                    "track_id": track_id,
                    "status": "already_in_playlist",
                }
            )
            continue
        if track_id and not dry_run:
            batch.append(track_id)
            added_songs.append(
                {
                    "title": title,
                    "artist": artist,
                    "track": track,
                    "track_id": track_id,
                    "status": "added",
                }
            )
            if len(batch) == batch_size:
                # Robust Spotify add with rate limit handling
                retries = 0
                while True:
                    try:
                        sp.playlist_add_items(playlist_id, batch)
                        break
                    except Exception as e:
                        retry_after = None
                        if hasattr(e, "headers") and hasattr(
                            getattr(e, "headers"), "get"
                        ):
                            retry_after = getattr(e, "headers").get("Retry-After")
                        if (
                            hasattr(e, "http_status")
                            and getattr(e, "http_status") == 429
                        ):
                            if retry_after is not None:
                                try:
                                    wait = max(float(retry_after), min_retry_after)
                                except Exception:
                                    wait = max(
                                        batch_delay * (backoff_factor**retries),
                                        min_retry_after,
                                    )
                            else:
                                wait = max(
                                    batch_delay * (backoff_factor**retries),
                                    min_retry_after,
                                )
                            logger.warning(
                                f"Spotify rate limit hit. Retrying after {wait:.1f}s (retry {retries+1}/{max_retries})..."
                            )
                            import time

                            time.sleep(wait)
                            retries += 1
                            if retries >= max_retries:
                                logger.error(
                                    "Max retries reached for Spotify rate limit. Skipping batch."
                                )
                                break
                        else:
                            logger.error(f"Spotify API error: {e}")
                            break
                batch.clear()
                import time

                time.sleep(batch_delay)
            added_count += 1
    # Final batch add if there are remaining tracks
    if batch and not dry_run:
        retries = 0
        while True:
            try:
                sp.playlist_add_items(playlist_id, batch)
                break
            except Exception as e:
                retry_after = None
                if hasattr(e, "headers") and hasattr(getattr(e, "headers"), "get"):
                    retry_after = getattr(e, "headers").get("Retry-After")
                if hasattr(e, "http_status") and getattr(e, "http_status") == 429:
                    if retry_after is not None:
                        try:
                            wait = max(float(retry_after), min_retry_after)
                        except Exception:
                            wait = max(
                                batch_delay * (backoff_factor**retries), min_retry_after
                            )
                    else:
                        wait = max(
                            batch_delay * (backoff_factor**retries), min_retry_after
                        )
                else:
                    wait = max(batch_delay * (backoff_factor**retries), min_retry_after)
                logger.warning(
                    f"Spotify rate limit hit. Retrying after {wait:.1f}s (retry {retries+1}/{max_retries})..."
                )
                import time

                time.sleep(wait)
                retries += 1
                if retries >= max_retries:
                    logger.error(
                        "Max retries reached for Spotify rate limit. Skipping batch."
                    )
                    break
            else:
                batch.clear()
                import time

                time.sleep(batch_delay)
                break

    # Helper to safely load a JSON list from file
    def safe_load_json_list(path):
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    # Write skipped (private/deleted) to a dedicated file, appending if file exists
    PRIVATE_DELETED_SONGS_PATH = os.path.join(OUTPUT_DIR, "private_deleted_songs.json")
    prev_skipped = safe_load_json_list(PRIVATE_DELETED_SONGS_PATH)
    with open(PRIVATE_DELETED_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(prev_skipped + skipped_songs, f, ensure_ascii=False, indent=2)

    # Write only not found on Spotify to not_found_songs.json, appending if file exists
    prev_not_found = safe_load_json_list(NOT_FOUND_SONGS_PATH)
    not_found_on_spotify = [
        s for s in not_found_songs if s.get("status") == "not_found"
    ]
    with open(NOT_FOUND_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            prev_not_found + not_found_on_spotify, f, ensure_ascii=False, indent=2
        )

    # --- Collect all YouTube entries (with possible duplicates and their URLs) ---
    all_yt_entries = []
    for idx, title in enumerate(titles):
        artist, track = parse_artist_track(title)
        yt_url = ""
        # If title is a dict with 'url', use that; else, leave as empty string
        if isinstance(title, dict):
            yt_url = title.get("url", "")
            yt_title = title.get("title", "")
        else:
            yt_title = title
        all_yt_entries.append(
            {
                "title": yt_title,
                "artist": artist,
                "track": track,
                "status": "from_youtube",
                "youtube_url": yt_url,
            }
        )
    ALL_YT_ENTRIES_PATH = os.path.join(OUTPUT_DIR, "all_youtube_entries.json")
    with open(ALL_YT_ENTRIES_PATH, "w", encoding="utf-8") as f:
        json.dump(all_yt_entries, f, ensure_ascii=False, indent=2)

    # --- Deduplicate before adding to Spotify and added_songs.json (applies to both dry-run and normal) ---
    unique_songs = {}
    for song in added_songs:
        key = (song.get("artist"), song.get("track"), song.get("title"))
        # Only keep the first occurrence
        if key not in unique_songs and all(k is not None for k in key):
            unique_songs[key] = song
    deduped_added_songs = list(unique_songs.values())
    # Write added songs as before, appending if file exists
    prev_added = safe_load_json_list(ADDED_SONGS_PATH)
    with open(ADDED_SONGS_PATH, "w", encoding="utf-8") as f:
        json.dump(prev_added + deduped_added_songs, f, ensure_ascii=False, indent=2)
    # For dry-run, also write deduped_added_songs to dryrun_temp/dryrun_added.json if needed
    dryrun_temp_dir = os.path.join(OUTPUT_DIR, "dryrun_temp")
    if not os.path.exists(dryrun_temp_dir):
        os.makedirs(dryrun_temp_dir)
    dryrun_added_path = os.path.join(dryrun_temp_dir, "dryrun_added.json")
    with open(dryrun_added_path, "w", encoding="utf-8") as f:
        json.dump(deduped_added_songs, f, ensure_ascii=False, indent=2)

    # --- all_results should be a superset of all other result files ---
    # Collect all results from deduped_added_songs, not_found_on_spotify, and skipped_songs
    all_results = []
    for s in deduped_added_songs:
        d = {k: safe_str(s.get(k)) for k in ["title", "artist", "track", "status"]}
        all_results.append(d)
    for s in not_found_on_spotify:
        d = {k: safe_str(s.get(k)) for k in ["title", "artist", "track", "status"]}
        all_results.append(d)
    for s in skipped_songs:
        d = {k: safe_str(s.get(k)) for k in ["title", "artist", "track", "status"]}
        all_results.append(d)
    ALL_RESULTS_PATH = os.path.join(OUTPUT_DIR, "all_results.json")
    with open(ALL_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    # For dry-run, also write to dryrun_temp/all_results.json
    dryrun_all_results_path = os.path.join(dryrun_temp_dir, "all_results.json")
    with open(dryrun_all_results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Log summary
    num_added = sum(1 for s in added_songs if s["status"] == "added")
    num_already = sum(1 for s in added_songs if s["status"] == "already_in_playlist")
    num_deleted_private = sum(
        1 for s in skipped_songs if s["status"] == "private_or_deleted"
    )
    num_missing = len(not_found_on_spotify)
    logger.info(
        f"Finished.\n"
        f"{num_added} tracks added to Spotify playlist {playlist_id}.\n"
        f"{num_already} tracks were already in playlist.\n"
        f"{num_deleted_private} tracks were deleted/private on YouTube.\n"
        f"{num_missing} tracks were missing on Spotify."
    )


def safe_str(val: object) -> str:
    return "" if val is None else str(val)


def main() -> None:
    """
    CLI entry point for yt2spotify. Parses arguments and runs sync_command.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync YouTube playlist to Spotify playlist"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync_parser = subparsers.add_parser(
        "sync", help="Sync a YouTube playlist to a Spotify playlist"
    )
    sync_parser.add_argument("yt_url", help="YouTube playlist URL")
    sync_parser.add_argument("playlist_id", help="Spotify playlist ID")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not add tracks to playlist, just log what would be added",
    )
    sync_parser.add_argument(
        "--no-progress", action="store_true", help="Disable progress bar"
    )
    sync_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output (sets log level to DEBUG)",
    )
    sync_parser.add_argument(
        "--yt-api-key", help="YouTube Data API v3 key (optional, enables API fallback)"
    )
    sync_parser.add_argument(
        "--config", help="Path to a TOML config file (overrides package default)"
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    if args.command == "sync":
        sync_command(
            yt_url=args.yt_url,
            playlist_id=args.playlist_id,
            dry_run=args.dry_run,
            no_progress=args.no_progress,
            verbose=args.verbose,
            yt_api=args.yt_api_key,
            progress_wrapper=None,
            config=config,
        )
