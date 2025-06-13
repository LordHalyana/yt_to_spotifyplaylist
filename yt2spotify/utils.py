import os
from dotenv import load_dotenv
import unicodedata
import re

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

def clean_title(title):
    title = unicodedata.normalize('NFKC', title).casefold()
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'(?i)\b(prod\.|ft\.|feat\.|official|audio|video|unreleased|music|visualizer|by|with|remix|version|explicit|clean|lyrics|lyric|clip|HD|HQ|\d{4})\b', '', title)
    title = re.sub(r'[-_]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def parse_artist_track(title):
    title = unicodedata.normalize('NFKC', title).casefold()
    title = re.sub(r'\[(feat\.|ft\.|featuring)[^\]]*\]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\((feat\.|ft\.|featuring)[^\)]*\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\u2013\u2014\u2212\u2022\u00b7\u2027\u2010\u2011\u2012\u2015\|/]', ' - ', title)
    title = re.sub(r'\s*-+\s*', ' - ', title)
    title = re.sub(r'\s+', ' ', title)
    trailing = r'(?i)\b(live|remaster(ed)?( \d{2,4})?|lyrics?|audio|video|version|explicit|clean|visualizer|clip|HD|HQ)\b.*$'
    title = re.sub(trailing, '', title).strip()
    if ' - ' in title:
        artist, track = title.split(' - ', 1)
        artist = re.split(r'(?i)\\b(feat\\.|ft\\.|featuring)\\b', artist)[0].strip()
        track = re.split(r'(?i)\\b(feat\\.|ft\\.|featuring)\\b', track)[0].strip()
        return artist, track
    return None, clean_title(title)
