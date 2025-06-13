from typing import List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from yt2spotify.yt_utils import get_yt_playlist_titles_yt_dlp

def get_yt_playlist_titles_api(api_key: str, playlist_id: str) -> List[str]:
    """
    Fetches YouTube playlist video titles using the YouTube Data API v3.
    Falls back to yt_dlp if quota is exceeded or key is missing/invalid.
    Args:
        api_key: YouTube Data API v3 key.
        playlist_id: YouTube playlist ID or URL.
    Returns:
        List of video titles as strings.
    """
    if not api_key:
        # Fallback if no key provided
        return get_yt_playlist_titles_yt_dlp(playlist_id)
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        # Extract playlist ID if a URL is given
        if 'list=' in playlist_id:
            import urllib.parse
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(playlist_id).query)
            playlist_id = qs.get('list', [playlist_id])[0]
        titles = []
        nextPageToken = None
        while True:
            request = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=nextPageToken
            )
            response = request.execute()
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                title = snippet.get('title')
                if title:
                    titles.append(title)
            nextPageToken = response.get('nextPageToken')
            if not nextPageToken:
                break
        return titles
    except HttpError as e:
        if e.resp.status == 403:
            # Quota exceeded or forbidden, fallback
            return get_yt_playlist_titles_yt_dlp(playlist_id)
        raise
    except Exception:
        # Any other error, fallback
        return get_yt_playlist_titles_yt_dlp(playlist_id)
