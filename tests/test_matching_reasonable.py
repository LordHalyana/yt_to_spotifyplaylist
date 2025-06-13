import pytest
from yt2spotify import matching

def test_is_reasonable_match_exact():
    assert matching.is_reasonable_match('Daft Punk', 'One More Time', 'Daft Punk', 'One More Time')

def test_is_reasonable_match_case_insensitive():
    assert matching.is_reasonable_match('daft punk', 'one more time', 'DAFT PUNK', 'ONE MORE TIME')

def test_is_reasonable_match_partial_artist():
    assert matching.is_reasonable_match('Daft', 'One More Time', 'Daft Punk', 'One More Time')

def test_is_reasonable_match_artist_mismatch():
    assert not matching.is_reasonable_match('Daft Punk', 'One More Time', 'Justice', 'One More Time')

def test_is_reasonable_match_title_mismatch():
    assert not matching.is_reasonable_match('Daft Punk', 'One More Time', 'Daft Punk', 'Digital Love')

def test_is_reasonable_match_empty_artist():
    assert matching.is_reasonable_match('', 'One More Time', 'Daft Punk', 'One More Time')

def test_is_reasonable_match_empty_title():
    assert not matching.is_reasonable_match('Daft Punk', '', 'Daft Punk', 'One More Time')

def test_is_reasonable_match_none_values():
    assert matching.is_reasonable_match(None, None, None, None)
