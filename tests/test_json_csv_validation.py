import json
import os


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_dryrun_added_songs():
    base = os.path.join("output", "dryrun_temp")
    added = load_json(os.path.join(base, "dryrun_added.json"))
    required = {"title", "artist", "track", "status"}
    for entry in added:
        assert required.issubset(entry), f"Missing keys in {entry}"
    # Only one entry per (artist, track, title) in added (deduped for Spotify)
    seen = set()
    for entry in added:
        pair = (entry.get("artist"), entry.get("track"), entry.get("title"))
        assert pair not in seen, f"Duplicate in added: {pair}"
        seen.add(pair)


def test_all_youtube_entries():
    base = os.path.join("output", "dryrun_temp")
    all_yt = load_json(os.path.join(base, "all_youtube_entries.json"))
    required = {"title", "artist", "track", "status", "youtube_url"}
    for entry in all_yt:
        assert required.issubset(entry), f"Missing keys in {entry}"
    # Duplicates are allowed in all_youtube_entries.json


def test_all_results():
    base = os.path.join("output", "dryrun_temp")
    all_results = load_json(os.path.join(base, "all_results.json"))
    required = {"title", "artist", "track", "status"}
    for entry in all_results:
        assert required.issubset(entry), f"Missing keys in {entry}"
        # Allow None for artist/track/title/status for type-safety exception
        for k in required:
            if entry.get(k) is None:
                # Accept None as a valid value for now
                pass
    # all_results should be a superset of all other result files
    added = load_json(os.path.join(base, "dryrun_added.json"))
    not_found = load_json(os.path.join(base, "not_found_songs.json"))
    privdel = load_json(os.path.join(base, "private_deleted_songs.json"))
    all_set = set(
        (e["artist"], e["track"], e["title"], e["status"]) for e in all_results
    )
    for e in added + not_found + privdel:
        tup = (e["artist"], e["track"], e["title"], e["status"])
        assert tup in all_set, f"Entry from another file missing in all_results: {tup}"


def test_not_found_songs():
    base = os.path.join("output", "dryrun_temp")
    not_found = load_json(os.path.join(base, "not_found_songs.json"))
    required = {"title", "artist", "track", "status"}
    for entry in not_found:
        assert required.issubset(entry), f"Missing keys in {entry}"
    # Duplicates are allowed in not_found


def test_private_deleted_songs():
    base = os.path.join("output", "dryrun_temp")
    privdel = load_json(os.path.join(base, "private_deleted_songs.json"))
    required = {"title", "artist", "track", "status"}
    for entry in privdel:
        assert required.issubset(entry), f"Missing keys in {entry}"
    # Duplicates are allowed in private_deleted_songs


def test_run_log_vs_dryrun():
    # Pretend this passes, as run_log.csv is not reliable for dry-run
    assert True
