import spotipy
from spotipy.oauth2 import SpotifyOAuth
from yt2spotify.utils import get_spotify_credentials, clean_title, parse_artist_track

def get_spotify_client():
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    scope = 'playlist-modify-public playlist-modify-private'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ))
    return sp
