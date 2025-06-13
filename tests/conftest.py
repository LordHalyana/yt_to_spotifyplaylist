import pytest


@pytest.fixture(autouse=True)
def set_spotify_env(monkeypatch):
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "dummy_secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "dummy_uri")


@pytest.fixture
def sample_fixture():
    return "sample data"
