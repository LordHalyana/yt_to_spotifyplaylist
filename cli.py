import argparse
from yt2spotify.spotify_utils import get_spotify_client
from yt2spotify.yt_utils import get_yt_playlist_titles_yt_dlp, get_yt_playlist_titles_api
from yt2spotify.utils import clean_title, parse_artist_track
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description='Sync YouTube playlist to Spotify playlist')
    parser.add_argument('yt_url', help='YouTube playlist URL')
    parser.add_argument('playlist_id', help='Spotify playlist ID')
    parser.add_argument('--dry-run', action='store_true', help='Do not add tracks to playlist, just log what would be added')
    parser.add_argument('--yt-api', help='YouTube Data API v3 key (optional)')
    args = parser.parse_args()

    # Fetch YouTube playlist titles
    if args.yt_api:
        titles = get_yt_playlist_titles_api(args.yt_url, args.yt_api)
    else:
        titles = get_yt_playlist_titles_yt_dlp(args.yt_url)

    # Authenticate with Spotify
    sp = get_spotify_client()

    # Progress bar setup
    added_count = 0
    with tqdm(total=len(titles), desc="Syncing", unit="track") as pbar:
        for idx, title in enumerate(titles, 1):
            # ...matching and adding logic goes here...
            # For now, just simulate add
            # If added:
            added_count += 1
            pbar.set_postfix({"added": added_count})
            pbar.update(1)

    print(f"Finished. {added_count} tracks added to Spotify playlist {args.playlist_id}.")

if __name__ == '__main__':
    main()
