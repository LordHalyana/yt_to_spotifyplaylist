import pytest
from yt2spotify import core

@pytest.mark.asyncio
async def test_async_spotify_search_batch_success(monkeypatch):
    # Patch aiohttp.ClientSession.get to return a dummy response
    class DummyResp:
        def __init__(self, status, json_data):
            self.status = status
            self._json = json_data
            self.headers = {'Content-Type': 'application/json'}
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def json(self): return self._json
        async def text(self): return str(self._json)
    class DummySession:
        def __init__(self): self.calls = []
        def get(self, url, headers=None):
            self.calls.append(url)
            return DummyResp(200, {"tracks": {"items": [{"id": "trackid123"}]}})
    session = DummySession()
    queries = [("Artist", "Title", "query")] 
    results = await core.async_spotify_search_batch("token", queries, session)
    assert results[0][2] == "trackid123"

@pytest.mark.asyncio
async def test_async_spotify_search_batch_429(monkeypatch):
    # Patch aiohttp.ClientSession.get to simulate 429 then success
    class DummyResp:
        def __init__(self, status, json_data=None, retry_after=1):
            self.status = status
            self._json = json_data or {}
            self.headers = {'Content-Type': 'application/json', 'Retry-After': str(retry_after)}
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def json(self): return self._json
        async def text(self): return str(self._json)
    class DummySession:
        def __init__(self): self.calls = 0
        def get(self, url, headers=None):
            self.calls += 1
            if self.calls == 1:
                return DummyResp(429, retry_after=0.01)
            return DummyResp(200, {"tracks": {"items": [{"id": "trackid429"}]}})
    session = DummySession()
    queries = [("Artist", "Title", "query")]
    results = await core.async_spotify_search_batch("token", queries, session)
    assert results[0][2] == "trackid429"

@pytest.mark.asyncio
async def test_async_search_with_cache(monkeypatch):
    class DummyCache:
        def get(self, a, t): return None
        def set(self, a, t, i): pass
    class DummySpotify:
        class DummyAuth:
            def get_access_token(self, as_dict=False): return "token"
        auth_manager = DummyAuth()
    async def dummy_batch(token, queries, session):
        return [(a, t, "id", {}) for a, t, _ in queries]
    monkeypatch.setattr(core, "async_spotify_search_batch", dummy_batch)
    sp = DummySpotify()
    queries = [("A", "B", "Q")]
    cache = DummyCache()
    results = await core.async_search_with_cache(sp, queries, cache)
    assert results[0][2] == "id"
