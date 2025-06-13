import spotipy
import asyncio
import aiohttp
from typing import List, Tuple, Optional, Any
from spotipy.oauth2 import SpotifyOAuth
from yt2spotify.utils import get_spotify_credentials
from yt2spotify.cache import TrackCache
from urllib.parse import quote

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
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get('entries', []) if info else []
        return [entry.get('title') for entry in entries if entry.get('title')]

# --- Spotify helpers ---
def get_spotify_client() -> spotipy.Spotify:
    """
    Returns an authenticated Spotipy client for Spotify API access.
    """
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    scope = 'playlist-modify-public playlist-modify-private'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ))
    return sp

async def async_spotify_search_batch(
    sp_token: str,
    queries: List[Tuple[str, str, str]],
    session: aiohttp.ClientSession
) -> List[Tuple[str, str, Optional[str], Any]]:
    """
    Performs batch Spotify track searches asynchronously.
    Args:
        sp_token: Spotify API token.
        queries: List of (artist, title, query_string) tuples.
        session: aiohttp session for HTTP requests.
    Returns:
        List of (artist, title, track_id or None, response_json) tuples.
    """
    headers = {"Authorization": f"Bearer {sp_token}"}
    results: List[Optional[Tuple[str, str, Optional[str], Any]]] = [None] * len(queries)
    backoff = 1.0
    max_backoff = 60.0
    tasks = []
    for i, (artist, title, query) in enumerate(queries):
        if not query.strip():
            # Log skipped queries
            print(f'Skipping: "{title}" - "{artist}" - in playlist - skipping (empty query)')
            continue
        url = f"https://api.spotify.com/v1/search?q={quote(query)}&type=track&limit=1"
        tasks.append((i, artist, title, url))
    async def fetch(idx: int, artist: str, title: str, url: str) -> Tuple[int, str, str, Optional[str], Any]:
        nonlocal backoff
        while True:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 429:
                    retry_after = float(resp.headers.get('Retry-After', backoff))
                    await asyncio.sleep(retry_after)
                    backoff = min(backoff * 2, max_backoff)
                    continue
                if resp.status != 200:
                    try:
                        text = await resp.text()
                    except Exception:
                        text = "<no response body>"
                    print(f"Spotify API error {resp.status} for {url}: {text}")
                    return (idx, artist, title, None, None)
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    text = await resp.text()
                    print(f"Unexpected content type {content_type} for {url}: {text}")
                    return (idx, artist, title, None, None)
                data = await resp.json()
                items = data.get('tracks', {}).get('items', [])
                track_id = items[0]['id'] if items else None
                await asyncio.sleep(1)  # Respectful 1 second delay between Spotify requests
                return (idx, artist, title, track_id, data)
    coros = [fetch(idx, artist, title, url) for idx, artist, title, url in tasks]
    for fut in asyncio.as_completed(coros):
        idx, artist, title, track_id, data = await fut
        results[idx] = (artist, title, track_id, data)
    return results  # type: ignore

async def async_search_with_cache(
    sp: Any,
    queries: List[Tuple[str, str, str]],
    cache: TrackCache
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
    results: List[Tuple[str, str, Optional[str]]] = [(artist, title, None) for artist, title, _ in queries]
    for i, (artist, title, query) in enumerate(queries):
        if not query.strip():
            print(f'Skipping: "{title}" - "{artist}" - in playlist - skipping (empty query)')
            continue
        cached_id = cache.get(artist, title)
        if cached_id:
            results[i] = (artist, title, cached_id)
        else:
            uncached.append((artist, title, query))
            uncached_idx.append(i)
    if uncached:
        token = sp.auth_manager.get_access_token(as_dict=False)
        async with aiohttp.ClientSession() as session:
            batch_results = await async_spotify_search_batch(token, uncached, session)
        for (artist, title, track_id, _), idx in zip(batch_results, uncached_idx):
            results[idx] = (artist, title, track_id)
    return results
