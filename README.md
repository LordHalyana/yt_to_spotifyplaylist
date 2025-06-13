# yt2spotify

[![Build Status](https://github.com/LordHalyana/yt_to_spotifyplaylist/actions/workflows/ci.yml/badge.svg)](https://github.com/LordHalyana/yt_to_spotifyplaylist/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/yt2spotify.svg)](https://badge.fury.io/py/yt2spotify)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sync YouTube playlists to Spotify playlists with robust matching, progress bar, structured logging, and regression-tested logic.

---

## 🚦 Quality Gates

- **Pre-commit hooks:**
  - [x] Gitleaks: Automated secret scanning with custom and standard rules (`.gitleaks.toml`)
  - [x] Ruff: Linting for Python code
  - [x] Pytest: All tests must pass before commit
- **Coverage:** 80%+ required (see `pyproject.toml`)
- **No hardcoded secrets:** Enforced by Gitleaks and reviewed in repo history

## Features

- Extracts track titles from YouTube playlists (yt-dlp or YouTube Data API v3)
- Cleans and parses titles for best Spotify match
- Adds tracks to a specified Spotify playlist, avoiding duplicates
- Progress bar with ETA using `tqdm` (disable with `--no-progress`)
- Structured logging with Rich
- TOML config file support (`--config`)
- Universal progress bar and CLI flags (`--no-progress`, `--verbose`)
- Async Spotify search pipeline with 1s delay between requests (respects API limits)
- Handles YouTube private/deleted videos and skips empty queries
- Output files: `output/added_songs.json`, `output/not_found_songs.json`, `output/missing_on_spotify.json` (with status fields)
- Local cache for (artist, title) → track_id (planned)
- Regression test suite for matching logic
- Secure credential management via `.env` or environment variables

## 🛡️ Security & CI

- **Gitleaks**: `.gitleaks.toml` with custom `SPOTIPY_...` and generic secret regexes
- **Pre-commit**: `.pre-commit-config.yaml` runs Gitleaks, Ruff, and Pytest on every commit
- **No secrets**: Repo and history are clean of 32+ char secrets and common credential patterns

## 🧪 Testing

- All tests in `tests/` run automatically on commit
- Coverage threshold: 80% (see `pyproject.toml`)
- Linting and type checks enforced

## 🚀 Quickstart

1. `pip install .[dev]`
2. `pre-commit install`
3. Add your `.env` with Spotify credentials
4. Run: `python -m yt2spotify ...` or use the CLI

## 🛠️ Development Setup

To enable automatic code formatting, linting, and secret scanning on every commit, install pre-commit hooks:

```sh
pre-commit install
```

This will ensure `ruff`, `black`, and `gitleaks` run before every commit.

## Development

- See `.pre-commit-config.yaml` for hooks
- See `.gitleaks.toml` for secret scanning rules
- See `pyproject.toml` for config, dependencies, and coverage

---

_This project is maintained with automated quality gates and secret scanning. All contributions are checked for security, lint, and test compliance before commit._

## Installation

You can install directly from GitHub:

```bash
pip install git+https://github.com/LordHalyana/yt_to_spotifyplaylist
```

Or, for local development:

```bash
pip install .[dev]
```

After install, run:

```bash
yt2spotify --help
```

## Usage

### CLI

```sh
# Basic usage with yt-dlp (default)
python -m yt2spotify sync <yt_url> <spotify_playlist_id> [--dry-run]

# Or, if installed as a package:
yt2spotify sync <yt_url> <spotify_playlist_id> [--dry-run]

# Use YouTube Data API v3 (if you have an API key):
yt2spotify sync <yt_url> <spotify_playlist_id> --yt-api-key <YOUR_YT_API_KEY>

# Use a custom config file:
yt2spotify sync <yt_url> <spotify_playlist_id> --config path/to/config.toml
```

#### CLI Flags

- `--dry-run`: Only logs what would be added, does not modify the playlist.
- `--no-progress`: Disable the progress bar and use plain logging.
- `--verbose`: Enable debug-level logging.
- `--yt-api-key`: Use the YouTube Data API v3 for playlist fetching (with fallback to yt-dlp on quota/missing key).
- `--config`: Path to a TOML config file (overrides package default).

#### Configurable Rate Limit & Batching (TOML)

You can control Spotify API batching and rate limit handling via your TOML config file:

```toml
# Number of tracks to add to Spotify in each batch (default: 25, max: 100)
batch_size = 25
# Delay (in seconds) between each batch addition to Spotify (default: 2.0)
batch_delay = 2.0
# Maximum number of retries for a batch if rate limited (default: 5)
max_retries = 5
# Exponential backoff factor for repeated 429s (default: 2.0)
backoff_factor = 2.0
```

- These options ensure robust handling of Spotify's API rate limits and allow tuning for large playlists or slow connections.
- The tool will respect the `Retry-After` header from Spotify and use exponential backoff if rate limited repeatedly.

#### Output Files

- `output/added_songs.json`: Tracks added to Spotify (with status: `added` or `already_in_playlist`).
- `output/not_found_songs.json`: Tracks not found on Spotify or skipped (with status: `not_found` or `private_or_deleted`).
- `output/missing_on_spotify.json`: Tracks still on YouTube but missing on Spotify (with title, artist, and status).
- `logs/run_log.csv`: (If enabled) Run log for debugging and audit.

#### Example Output

```
Finished.
548 tracks added to Spotify playlist 53nCceptoTItuwCWUIAlXr.
19 tracks were deleted/private on YouTube.
392 tracks were missing on Spotify.
```

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
  - `core.py` — Core sync and async logic
  - `spotify_utils.py` — Spotify API helpers
  - `yt_utils.py` — YouTube extraction helpers
  - `utils.py` — Cleaning and parsing helpers
  - `matching.py` — Matching logic
  - `cache.py` — (Planned) Local cache
  - `youtube.py` — YouTube Data API fallback
- `output/` — Output data files (added, not found, missing)
- `logs/` — Log files
- `tests/` — Test suite (regression and unit tests)
- `.env` — Your credentials (never commit this!)
- `pyproject.toml` — Project configuration and dependencies
- `example_env.txt` — Example environment file

## License

MIT License. See [LICENSE](LICENSE).

## Troubleshooting the CLI on Windows

If you see errors like:

```
yt2spotify : The term 'yt2spotify' is not recognized as the name of a cmdlet...
```

or

```
ModuleNotFoundError: No module named 'yt2spotify'
```

Try the following steps:

1. **Check your Python and pip versions:**

   ```powershell
   python --version
   pip --version
   ```

   Ensure both use the same Python installation (e.g., Python 3.11).

2. **Find where yt2spotify was installed:**

   ```powershell
   pip show yt2spotify
   ```

   Look for the `Location:` and `Scripts` directory.

3. **Add the Scripts directory to your PATH for this session:**

   ```powershell
   $env:PATH = "<path-to-Scripts>;$env:PATH"
   yt2spotify --help
   ```

   Replace `<path-to-Scripts>` with the path from step 2, e.g.,
   `C:\Users\<username>\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts`

4. **If you still get errors, use the Python module directly:**
   ```powershell
   python -m yt2spotify.cli --help
   ```

If you continue to have issues, try uninstalling and reinstalling:

```powershell
pip uninstall yt2spotify
pip install . --no-warn-script-location
```

---

**Note:** This project is for educational/personal use. Respect the terms of service of YouTube and Spotify.
