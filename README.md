# yt2spotify

Sync YouTube playlists to Spotify playlists with robust matching, progress bar, and regression-tested logic.

## Features

- Extracts track titles from YouTube playlists (yt-dlp or YouTube Data API v3)
- Cleans and parses titles for best Spotify match
- Adds tracks to a specified Spotify playlist, avoiding duplicates
- Progress bar with ETA using `tqdm`
- Async Spotify search pipeline (planned)
- Local SQLite cache for (artist, title) → track_id (planned)
- Regression test suite for matching logic
- Secure credential management via `.env` or environment variables

## Installation

1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd yt_to_spotifyplaylist
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Copy and edit the example environment file:
   ```sh
   cp example_env.txt .env
   # Fill in your Spotify credentials in .env
   ```

## Usage

### CLI

```sh
# Basic usage with yt-dlp (default)
python -m yt2spotify <yt_url> <spotify_playlist_id> [--dry-run]

# Or, if installed as a package:
yt2spotify <yt_url> <spotify_playlist_id> [--dry-run]

# Use YouTube Data API v3 (if you have an API key):
yt2spotify <yt_url> <spotify_playlist_id> --yt-api <YOUR_YT_API_KEY>
```

- `--dry-run`: Only logs what would be added, does not modify the playlist.
- Progress bar shows total, processed, and added tracks.

## Credentials

Set the following in your `.env` file or environment:

```
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=https://127.0.0.1/auth-response
```

## Testing

Run the regression and unit tests:

```sh
pytest
```

## Project Structure

- `yt2spotify/` — Main package modules
  - `cli.py` — CLI entry point
  - `spotify_utils.py` — Spotify API helpers
  - `yt_utils.py` — YouTube extraction helpers
  - `utils.py` — Cleaning and parsing helpers
- `tests/` — Test suite (regression and unit tests)
- `.env` — Your credentials (never commit this!)
- `requirements.txt` — Python dependencies
- `example_env.txt` — Example environment file

## License

MIT

---

**Note:** This project is for educational/personal use. Respect the terms of service of YouTube and Spotify.
