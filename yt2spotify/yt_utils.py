import yt_dlp
from yt2spotify.utils import clean_title, parse_artist_track

def get_yt_playlist_titles_yt_dlp(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'force_generic_extractor': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get('entries', [])
        return [entry.get('title') for entry in entries if entry.get('title')]

# Placeholder for YouTube Data API v3 support
def get_yt_playlist_titles_api(playlist_url, api_key):
    raise NotImplementedError('YouTube Data API v3 support not yet implemented')
