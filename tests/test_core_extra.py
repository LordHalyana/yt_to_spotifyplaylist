import pytest
from yt2spotify import core

@pytest.mark.asyncio
async def test_async_spotify_search_batch_non_200(monkeypatch):
    # Simulate a non-200 response (e.g., 500)
    class DummyResp:
        status = 500
        headers = {'Content-Type': 'application/json'}
        async def text(self):
            return 'error!'
        async def json(self):
            return {}
    class DummyContext:
        async def __aenter__(self): return DummyResp()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummySession:
        def get(self, url, headers=None):
            return DummyContext()
    token = 'fake_token'
    queries = [('artist', 'title', 'query')]
    results = await core.async_spotify_search_batch(token, queries, DummySession())  # type: ignore
    assert results[0][2] is None  # track_id should be None

@pytest.mark.asyncio
async def test_async_spotify_search_batch_unexpected_content_type(monkeypatch):
    # Simulate a response with unexpected content type
    class DummyResp:
        status = 200
        headers = {'Content-Type': 'text/html'}
        async def text(self):
            return '<html></html>'
        async def json(self):
            return {}
    class DummyContext:
        async def __aenter__(self): return DummyResp()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummySession:
        def get(self, url, headers=None):
            return DummyContext()
    token = 'fake_token'
    queries = [('artist', 'title', 'query')]
    results = await core.async_spotify_search_batch(token, queries, DummySession())  # type: ignore
    assert results[0][2] is None

@pytest.mark.asyncio
async def test_async_spotify_search_batch_empty_items(monkeypatch):
    # Simulate a valid response but no items
    class DummyResp:
        status = 200
        headers = {'Content-Type': 'application/json'}
        async def text(self):
            return '{}'
        async def json(self):
            return {'tracks': {'items': []}}
    class DummyContext:
        async def __aenter__(self): return DummyResp()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummySession:
        def get(self, url, headers=None):
            return DummyContext()
    token = 'fake_token'
    queries = [('artist', 'title', 'query')]
    results = await core.async_spotify_search_batch(token, queries, DummySession())  # type: ignore
    assert results[0][2] is None
