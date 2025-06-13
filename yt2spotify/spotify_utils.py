import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Any
from yt2spotify.utils import get_spotify_credentials


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


def spotify_search(sp: spotipy.Spotify, query: str, limit: int = 1) -> dict[str, Any]:
    """
    Performs a Spotify search for tracks.
    Args:
        sp: Spotipy client.
        query: Search query string.
        limit: Number of results to return (default 1).
    Returns:
        Spotify API search result as a dictionary.
    """
    result = sp.search(q=query, type="track", limit=limit)
    if not isinstance(result, dict):
        return {}
    return result
