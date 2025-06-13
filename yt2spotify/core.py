import spotipy
from typing import List, Tuple, Optional, Any
from spotipy.oauth2 import SpotifyOAuth
from yt2spotify.utils import get_spotify_credentials
from yt2spotify.cache import TrackCache
from urllib.parse import quote
from yt2spotify.logging_config import logger


# --- YouTube helpers ---
def get_yt_playlist_titles(playlist_url: str) -> List[str]:
    """
    Extracts video titles from a YouTube playlist URL using yt-dlp.
    Args:
        playlist_url: The URL of the YouTube playlist.
    Returns:
        A list of video titles as strings.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "force_generic_extractor": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get("entries", []) if info else []
        return [entry.get("title") for entry in entries if entry.get("title")]


# --- Spotify helpers ---
def get_spotify_client() -> spotipy.Spotify:
    """
    Returns an authenticated Spotipy client for Spotify API access.
    """
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    scope = "playlist-modify-public playlist-modify-private"
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )
    )
    return sp


def sync_spotify_search(
    sp: spotipy.Spotify, queries: List[Tuple[str, str, str]]
) -> List[Tuple[str, str, Optional[str]]]:
    """
    Performs synchronous Spotify track searches.
    Args:
        sp: Authenticated Spotipy client.
        queries: List of (artist, title, query_string) tuples.
    Returns:
        List of (artist, title, track_id or None) tuples.
    """
    results: List[Tuple[str, str, Optional[str]]] = []
    for artist, title, query in queries:
        if not query.strip():
            logger.info(
                f'Skipping: "{title}" - "{artist}" - in playlist - skipping (empty query)'
            )
            results.append((artist, title, None))
            continue
        logger.info(f"Searching for: {title} - {artist}")
        try:
            response = sp.search(q=quote(query), type="track", limit=1)
            tracks = response.get("tracks") if response else None
            items = tracks.get("items", []) if tracks else []
            track_id = items[0]["id"] if items else None
            results.append((artist, title, track_id))
        except Exception as e:
            logger.warning(f"Error searching for {title} - {artist}: {e}")
            results.append((artist, title, None))
    return results


def sync_search_with_cache(
    sp: Any, queries: List[Tuple[str, str, str]], cache: TrackCache
) -> List[Tuple[str, str, Optional[str]]]:
    """
    Performs Spotify search with local cache for (artist, title) to track_id.
    Args:
        sp: Spotipy client.
        queries: List of (artist, title, query_string) tuples.
        cache: TrackCache instance.
    Returns:
        List of (artist, title, track_id or None) tuples.
    """
    uncached: List[Tuple[str, str, str]] = []
    uncached_idx: List[int] = []
    results: List[Tuple[str, str, Optional[str]]] = [
        (artist, title, None) for artist, title, _ in queries
    ]
    for i, (artist, title, query) in enumerate(queries):
        if not query.strip():
            logger.info(
                f'Skipping: "{title}" - "{artist}" - in playlist - skipping (empty query)'
            )
            continue
        cached_id = cache.get(artist, title)
        if cached_id:
            results[i] = (artist, title, cached_id)
        else:
            uncached.append((artist, title, query))
            uncached_idx.append(i)
    if uncached:
        batch_results = sync_spotify_search(sp, uncached)
        for (artist, title, track_id), idx in zip(batch_results, uncached_idx):
            results[idx] = (artist, title, track_id)
    return results
