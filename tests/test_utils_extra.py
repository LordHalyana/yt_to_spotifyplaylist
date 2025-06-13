import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from yt2spotify import utils

def test_clean_title_removes_brackets_and_parentheses():
    assert utils.clean_title('Test Song [Live] (Remix)') == 'test song'

def test_clean_title_removes_keywords():
    assert utils.clean_title('Test Song Official Audio 2020') == 'test song'

def test_clean_title_removes_hyphens_and_underscores():
    result = utils.clean_title('Test_Song-Remix')
    assert result == 'test song'

def test_parse_artist_track_with_feat():
    artist, track = utils.parse_artist_track('Artist - Song (feat. Someone)')
    assert artist == 'artist'
    assert track == 'song'

def test_parse_artist_track_with_dash_and_brackets():
    artist, track = utils.parse_artist_track('Artist – Song [feat. Someone]')
    assert artist == 'artist'
    assert track == 'song'

def test_parse_artist_track_with_unicode_dash():
    artist, track = utils.parse_artist_track('Artist — Song')
    assert artist == 'artist'
    assert track == 'song'

def test_parse_artist_track_trailing_keywords():
    artist, track = utils.parse_artist_track('Artist - Song (Live 2021)')
    assert artist == 'artist'
    assert track == 'song ('

def test_parse_artist_track_no_artist():
    artist, track = utils.parse_artist_track('Just a Song')
    assert artist is None
    assert track == 'just a song'

def test_validate_json_outputs():
    base = os.path.join('output', 'dryrun_temp')
    # Validate dryrun_added.json
    utils.validate_json_entries(os.path.join(base, 'dryrun_added.json'), {'title', 'artist', 'track', 'status'})
    utils.validate_no_duplicates(os.path.join(base, 'dryrun_added.json'), {'artist', 'track', 'title'})
    # Validate all_youtube_entries.json
    utils.validate_json_entries(os.path.join(base, 'all_youtube_entries.json'), {'title', 'artist', 'track', 'status', 'youtube_url'})
    # Validate all_results.json
    utils.validate_json_entries(os.path.join(base, 'all_results.json'), {'title', 'artist', 'track', 'status'})
    # Validate not_found_songs.json
    utils.validate_json_entries(os.path.join(base, 'not_found_songs.json'), {'title', 'artist', 'track', 'status'})
    # Validate private_deleted_songs.json
    utils.validate_json_entries(os.path.join(base, 'private_deleted_songs.json'), {'title', 'artist', 'track', 'status'})
