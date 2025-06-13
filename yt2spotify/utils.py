import json
import os
from typing import Set, Tuple, Optional
from dotenv import load_dotenv
import unicodedata
import re


def get_spotify_credentials() -> Tuple[str, str, str]:
    """
    Loads Spotify credentials from environment or .env file.
    Returns:
        Tuple of (client_id, client_secret, redirect_uri).
    Raises:
        RuntimeError: If any credential is missing.
    """
    load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
    missing = []
    if not client_id:
        missing.append("SPOTIPY_CLIENT_ID")
    if not client_secret:
        missing.append("SPOTIPY_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("SPOTIPY_REDIRECT_URI")
    if missing:
        raise RuntimeError(
            f"Missing required Spotify credentials: {', '.join(missing)}. Set them in your environment or a .env file."
        )
    # mypy: assert all are str
    assert (
        client_id is not None and client_secret is not None and redirect_uri is not None
    )
    return client_id, client_secret, redirect_uri


def clean_title(title: str) -> str:
    """
    Cleans and normalizes a track title for matching/searching.
    Args:
        title: The original title string.
    Returns:
        A cleaned, normalized title string.
    """
    title = unicodedata.normalize("NFKC", title).casefold()
    # Replace all dash-like unicode characters with a space
    title = re.sub(
        r"[\u2013\u2014\u2212\u2022\u00b7\u2027\u2010\u2011\u2012\u2015]", " ", title
    )
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(
        r"(?i)\b(prod\.|ft\.|feat\.|official|audio|video|unreleased|music|visualizer|by|with|remix|version|explicit|clean|lyrics|lyric|clip|HD|HQ|\d{4})\b",
        "",
        title,
    )
    title = re.sub(r"[-_]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def parse_artist_track(title: str) -> Tuple[Optional[str], str]:
    """
    Attempts to parse an artist and track from a title string.
    Args:
        title: The original title string.
    Returns:
        Tuple of (artist, track). Artist may be None if not found.
    """
    title = unicodedata.normalize("NFKC", title).casefold()
    # Remove feat/ft in brackets
    title = re.sub(r"\[(feat\.|ft\.|featuring)[^\]]*\]", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\((feat\.|ft\.|featuring)[^\)]*\)", "", title, flags=re.IGNORECASE)
    # Replace all dash-like unicode characters with a dash
    title = re.sub(
        r"[\u2013\u2014\u2212\u2022\u00b7\u2027\u2010\u2011\u2012\u2015\|/]+",
        " - ",
        title,
    )
    title = re.sub(r"\s*-+\s*", " - ", title)
    title = re.sub(r"\s+", " ", title)
    trailing = r"(?i)\b(live|remaster(ed)?( \d{2,4})?|lyrics?|audio|video|version|explicit|clean|visualizer|clip|HD|HQ)\b.*$"
    title = re.sub(trailing, "", title).strip()
    if " - " in title:
        artist, track = title.split(" - ", 1)
        # Remove feat/ft from artist and track
        artist = re.split(r"(?i)\b(feat\.|ft\.|featuring)\b", artist)[0].strip()
        track = re.split(r"(?i)\b(feat\.|ft\.|featuring)\b", track)[0].strip()
        # Remove trailing dashes and spaces
        track = re.sub(r"[-\s]+$", "", track).strip()
        # Remove trailing 'ft.', 'feat.', etc. from the end of the track
        track = re.sub(r"(?i)(\s*(ft\.|feat\.|featuring)\s*.*)$", "", track).strip()
        # Remove trailing parenthesis/brackets and their contents from the end of the track
        track = re.sub(r"(\s*[\[(][^\])\]]*[\])\]]\s*)+$", "", track).strip()
        # Remove any unmatched trailing parenthesis or brackets left after previous removals
        track = re.sub(r"[\[(]+$", "", track).strip()
        return artist, track
    return None, clean_title(title)


def validate_json_entries(json_path: str, required_keys: Set[str]) -> None:
    """
    Validates that all entries in the given JSON file contain the required keys.
    Raises AssertionError if any entry is missing required keys.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for entry in data:
        assert required_keys.issubset(entry), f"Missing keys in {entry}"


def validate_no_duplicates(json_path: str, key_fields: Set[str]) -> None:
    """
    Validates that there are no duplicate entries in the JSON file based on key_fields.
    Raises AssertionError if duplicates are found.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    seen = set()
    for entry in data:
        pair = tuple(entry.get(k) for k in key_fields)
        assert pair not in seen, f"Duplicate in added: {pair}"
        seen.add(pair)
