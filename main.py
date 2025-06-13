import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import yt_dlp
import time
import re
import json
import unicodedata
import requests
import csv
from datetime import datetime
import argparse
from yt2spotify.utils import clean_title, parse_artist_track

# Set your credentials here or use environment variables
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID', '42f3e2b2a98348249fe782ebc706aede')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET', '9f8a9e9bd0ad4f00b515b9b9af5f93ce')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI', 'https://127.0.0.1/auth-response')

# Step 1: Get YouTube playlist URL from user
#yt_playlist_url = input('Enter YouTube playlist URL: ')
yt_playlist_url = "https://www.youtube.com/playlist?list=PLE4B85EC96395A67D"
# Step 2: Extract video titles from YouTube playlist using yt-dlp

def get_yt_playlist_titles(playlist_url):
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

song_titles = get_yt_playlist_titles(yt_playlist_url)

# Step 3: Authenticate with Spotify
scope = 'playlist-modify-public playlist-modify-private'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=scope
))
user_id = sp.current_user()['id']

# Step 4: Use a specific existing Spotify playlist by ID
playlist_name = "Baffe Blast"
spotify_playlist_id = "53nCceptoTItuwCWUIAlXr"

# Fetch existing track IDs in the playlist to avoid duplicates
existing_track_ids = set()
offset = 0
while True:
    response = sp.playlist_items(spotify_playlist_id, offset=offset, fields='items.track.id,total', additional_types=['track'])
    items = response['items']
    if not items:
        break
    for item in items:
        track = item.get('track')
        if track and track.get('id'):
            existing_track_ids.add(track['id'])
    offset += len(items)
    if len(items) == 0:
        break
print(f"Found {len(existing_track_ids)} existing tracks in playlist '{playlist_name}'.")

# Load previously added track IDs from added_songs.json
try:
    with open('added_songs.json', 'r', encoding='utf-8') as f:
        _added_songs_data = json.load(f)
        previously_added_ids = set()
        for entry in _added_songs_data:
            # Try to extract Spotify track ID from the entry if present
            # If not present, fallback to matching by (added_artist, added_title)
            # But for now, we only have artist/title, so we will build a set of (artist.lower(), title.lower())
            if 'added_artist' in entry and 'added_title' in entry:
                previously_added_ids.add((entry['added_artist'].casefold(), entry['added_title'].casefold()))
except Exception:
    previously_added_ids = set()

def try_fallback_search(title):
    # Try a less strict search if the strict one fails
    cleaned = clean_title(title)
    print(f"    Fallback search: {cleaned}")
    result = sp.search(q=cleaned, type='track', limit=3)
    tracks = result['tracks']['items']
    if tracks:
        # Return the best match
        track_id = tracks[0]['id']
        track_name = tracks[0]['name']
        artist_name = tracks[0]['artists'][0]['name']
        print(f"    Fallback found: {track_name} by {artist_name} (ID: {track_id}) - Adding to playlist.")
        return track_id, track_name, artist_name
    return None, None, None

# Helper to check if fallback result is a reasonable match
from difflib import SequenceMatcher
try:
    from rapidfuzz.fuzz import token_set_ratio
    from rapidfuzz.distance import JaroWinkler
except ImportError:
    # Fallback if rapidfuzz is not installed
    token_set_ratio = None
    JaroWinkler = None

def is_reasonable_match(searched_artist, searched_title, found_artist, found_title):
    # Lowercase and remove extra spaces
    searched_artist = (searched_artist or '').lower().strip()
    searched_title = (searched_title or '').lower().strip()
    found_artist = (found_artist or '').lower().strip()
    found_title = (found_title or '').lower().strip()
    # All words in searched artist must be in found artist
    artist_match = all(word in found_artist for word in searched_artist.split() if word)
    if not artist_match:
        return False
    # Jaro-Winkler similarity
    jw_score = 0
    tsr_score = 0
    if JaroWinkler:
        jw_score = JaroWinkler.normalized_similarity(searched_title, found_title)
    else:
        jw_score = SequenceMatcher(None, searched_title, found_title).ratio()
    if token_set_ratio:
        tsr_score = token_set_ratio(searched_title, found_title)
    else:
        # Fallback: simple token overlap ratio
        searched_set = set(searched_title.split())
        found_set = set(found_title.split())
        if searched_set:
            tsr_score = 100 * len(searched_set & found_set) / len(searched_set)
        else:
            tsr_score = 0
    # Jaro-Winkler >= 0.90 or token_set_ratio >= 95
    return (jw_score >= 0.90) or (tsr_score >= 95)

added_songs = []
not_found_songs = []
track_ids = []
current_playlist_size = len(existing_track_ids)
# Exponential back-off for rate limiting
sleep_time = 0.5
max_sleep = 10.0
min_sleep = 0.5
backoff_factor = 1.5

def get_adaptive_batch_size(current_playlist_size):
    mod = current_playlist_size % 100
    return min(25, 100 - mod) if mod != 0 else 25

def adaptive_sleep(last_was_429):
    global sleep_time
    if last_was_429:
        sleep_time = min(sleep_time * backoff_factor, max_sleep)
    else:
        sleep_time = max(min_sleep, sleep_time * 0.95)
    time.sleep(sleep_time)

# --- Logging setup ---
run_log_path = 'run_log.csv'
run_log_fields = ['timestamp', 'searched_artist', 'searched_title', 'found_artist', 'found_title', 'status']
def log_run(searched_artist, searched_title, found_artist, found_title, status):
    with open(run_log_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=run_log_fields)
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerow({
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'searched_artist': searched_artist,
            'searched_title': searched_title,
            'found_artist': found_artist,
            'found_title': found_title,
            'status': status
        })

# --- Argument parser ---
parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Do not add tracks to playlist, just log what would be added')
args = parser.parse_args()
dryrun_added = []

for idx, title in enumerate(song_titles, 1):
    artist, track = parse_artist_track(title)
    if artist:
        query = f"artist:{artist} track:{track}".strip()
    else:
        query = clean_title(title)
    query = query.strip()
    if not query:
        print(f"[{idx}/{len(song_titles)}] Skipping empty query for title: {title}")
        not_found_songs.append({"searched_artist": artist, "searched_title": track, "original_title": title})
        continue
    print(f"[{idx}/{len(song_titles)}] Searching for: {query}")
    print(f"    (Spotify search query: {query})")
    result = sp.search(q=query, type='track', limit=1)
    tracks = result['tracks']['items']
    found = False
    last_was_429 = False
    if tracks:
        track_id = tracks[0]['id']
        track_name = tracks[0]['name']
        artist_name = tracks[0]['artists'][0]['name']
        # Check against both live playlist and previously added songs
        if (artist_name.casefold(), track_name.casefold()) in previously_added_ids or track_id in existing_track_ids:
            print(f"  Already in playlist or previously added: {track_name} by {artist_name} (ID: {track_id}) - Skipping.")
            log_run(artist, track, artist_name, track_name, 'Duplicate')
            found = True
        else:
            print(f"  Found: {track_name} by {artist_name} (ID: {track_id}) - Adding to playlist.")
            if args.dry_run:
                dryrun_added.append(track_id)
            else:
                track_ids.append(track_id)
            added_songs.append({
                "searched_artist": artist,
                "searched_title": track,
                "added_artist": artist_name,
                "added_title": track_name,
                "original_title": title
            })
            previously_added_ids.add((artist_name.casefold(), track_name.casefold()))
            log_run(artist, track, artist_name, track_name, 'Correct')
            found = True
    if not found:
        # Try fallback search
        fallback_id, fallback_name, fallback_artist = try_fallback_search(title)
        if fallback_id and is_reasonable_match(artist, track, fallback_artist, fallback_name):
            if (fallback_artist.casefold(), fallback_name.casefold()) in previously_added_ids or fallback_id in existing_track_ids:
                print(f"    Already in playlist or previously added: {fallback_name} by {fallback_artist} (ID: {fallback_id}) - Skipping.")
                log_run(artist, track, fallback_artist, fallback_name, 'Duplicate')
            else:
                print(f"    Fallback found: {fallback_name} by {fallback_artist} (ID: {fallback_id}) - Adding to playlist.")
                if args.dry_run:
                    dryrun_added.append(fallback_id)
                else:
                    track_ids.append(fallback_id)
                added_songs.append({
                    "searched_artist": artist,
                    "searched_title": track,
                    "added_artist": fallback_artist,
                    "added_title": fallback_name,
                    "original_title": title
                })
                previously_added_ids.add((fallback_artist.casefold(), fallback_name.casefold()))
                log_run(artist, track, fallback_artist, fallback_name, 'Correct')
        else:
            # --- Second-pass artist-only search ---
            found_second_pass = False
            if artist and track:
                # Remove common stopwords from track for search
                stopwords = {'the','a','an','and','or','of','in','on','to','for','with','by','at','from','feat','ft','featuring','remix','version','edit','mix','live','remaster','remastered','explicit','clean','lyrics','lyric','audio','video','clip','visualizer','hd','hq'}
                cleaned_track = ' '.join([w for w in track.split() if w.lower() not in stopwords])
                # 1. Try artist:{artist} track:{cleaned_track}
                query1 = f"artist:{artist} track:{cleaned_track}".strip()
                print(f"    Second-pass search: {query1}")
                result1 = sp.search(q=query1, type='track', limit=2)
                tracks1 = result1['tracks']['items']
                for t in tracks1:
                    # Use Jaro-Winkler for strict title similarity
                    jw_score = 0
                    if JaroWinkler:
                        jw_score = JaroWinkler.normalized_similarity(track.lower(), t['name'].lower())
                    else:
                        jw_score = SequenceMatcher(None, track.lower(), t['name'].lower()).ratio()
                    if jw_score >= 0.92:
                        track_id = t['id']
                        artist_name2 = t['artists'][0]['name']
                        track_name2 = t['name']
                        if (artist_name2.casefold(), track_name2.casefold()) in previously_added_ids or track_id in existing_track_ids:
                            print(f"    Already in playlist or previously added: {track_name2} by {artist_name2} (ID: {track_id}) - Skipping.")
                            log_run(artist, track, artist_name2, track_name2, 'Duplicate')
                        else:
                            print(f"    Second-pass found: {track_name2} by {artist_name2} (ID: {track_id}) - Adding to playlist.")
                            if args.dry_run:
                                dryrun_added.append(track_id)
                            else:
                                track_ids.append(track_id)
                            added_songs.append({
                                "searched_artist": artist,
                                "searched_title": track,
                                "added_artist": artist_name2,
                                "added_title": track_name2,
                                "original_title": title
                            })
                            previously_added_ids.add((artist_name2.casefold(), track_name2.casefold()))
                            log_run(artist, track, artist_name2, track_name2, 'Correct')
                        found_second_pass = True
                        break
                # 2. Try artist:{artist} {track} (no 'track:' qualifier)
                if not found_second_pass:
                    query2 = f"artist:{artist} {track}".strip()
                    print(f"    Second-pass search: {query2}")
                    result2 = sp.search(q=query2, type='track', limit=2)
                    tracks2 = result2['tracks']['items']
                    for t in tracks2:
                        jw_score = 0
                        if JaroWinkler:
                            jw_score = JaroWinkler.normalized_similarity(track.lower(), t['name'].lower())
                        else:
                            jw_score = SequenceMatcher(None, track.lower(), t['name'].lower()).ratio()
                        if jw_score >= 0.92:
                            track_id = t['id']
                            artist_name2 = t['artists'][0]['name']
                            track_name2 = t['name']
                            if (artist_name2.casefold(), track_name2.casefold()) in previously_added_ids or track_id in existing_track_ids:
                                print(f"    Already in playlist or previously added: {track_name2} by {artist_name2} (ID: {track_id}) - Skipping.")
                                log_run(artist, track, artist_name2, track_name2, 'Duplicate')
                            else:
                                print(f"    Second-pass found: {track_name2} by {artist_name2} (ID: {track_id}) - Adding to playlist.")
                                if args.dry_run:
                                    dryrun_added.append(track_id)
                                else:
                                    track_ids.append(track_id)
                                added_songs.append({
                                    "searched_artist": artist,
                                    "searched_title": track,
                                    "added_artist": artist_name2,
                                    "added_title": track_name2,
                                    "original_title": title
                                })
                                previously_added_ids.add((artist_name2.casefold(), track_name2.casefold()))
                                log_run(artist, track, artist_name2, track_name2, 'Correct')
                            found_second_pass = True
                            break
            if not found_second_pass:
                print(f"  Not found on Spotify.")
                not_found_songs.append({"searched_artist": artist, "searched_title": track, "original_title": title})
                log_run(artist, track, '', '', 'Not found')
    # Add in adaptive batches as soon as batch is ready
    batch_size = get_adaptive_batch_size(current_playlist_size + len(track_ids))
    if len(track_ids) >= batch_size:
        print(f"Adding batch of {len(track_ids)} tracks to playlist...")
        try:
            sp.playlist_add_items(spotify_playlist_id, track_ids)
            current_playlist_size += len(track_ids)
            track_ids.clear()
            last_was_429 = False
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                print("    Hit Spotify rate limit (429). Backing off...")
                last_was_429 = True
            else:
                raise
    adaptive_sleep(last_was_429)

# Add any remaining tracks (less than batch size)
if track_ids:
    print(f"Adding final batch of {len(track_ids)} tracks to playlist...")
    last_was_429 = False
    try:
        sp.playlist_add_items(spotify_playlist_id, track_ids)
        current_playlist_size += len(track_ids)
        last_was_429 = False
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 429:
            print("    Hit Spotify rate limit (429). Backing off...")
            last_was_429 = True
        else:
            raise
    adaptive_sleep(last_was_429)

# Save not found songs and added songs to JSON files
with open('not_found_songs.json', 'w', encoding='utf-8') as f:
    json.dump(not_found_songs, f, ensure_ascii=False, indent=2)
with open('added_songs.json', 'w', encoding='utf-8') as f:
    json.dump(added_songs, f, ensure_ascii=False, indent=2)
if args.dry_run:
    with open('dryrun_added.json', 'w', encoding='utf-8') as f:
        json.dump(dryrun_added, f, ensure_ascii=False, indent=2)

print(f"Finished adding new tracks to Spotify playlist '{playlist_name}'.")
print(f"{len(not_found_songs)} songs were not found and saved to not_found_songs.json.")
print(f"{len(added_songs)} songs were added and saved to added_songs.json.")
print(f"Run log saved to {run_log_path}.")