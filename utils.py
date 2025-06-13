import os
from dotenv import load_dotenv
from yt2spotify.utils import clean_title, parse_artist_track

def get_spotify_credentials():
    load_dotenv()
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')
    missing = []
    if not client_id:
        missing.append('SPOTIPY_CLIENT_ID')
    if not client_secret:
        missing.append('SPOTIPY_CLIENT_SECRET')
    if not redirect_uri:
        missing.append('SPOTIPY_REDIRECT_URI')
    if missing:
        raise RuntimeError(f"Missing required Spotify credentials: {', '.join(missing)}. Set them in your environment or a .env file.")
    return client_id, client_secret, redirect_uri
