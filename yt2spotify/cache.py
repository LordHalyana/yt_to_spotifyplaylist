import sqlite3
from contextlib import closing
import threading
from typing import Optional

DB_PATH = 'cache.sqlite'

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS track_cache (
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    track_id TEXT NOT NULL,
    PRIMARY KEY (artist, title)
);
'''

class TrackCache:
    """
    SQLite-backed cache for (artist, title) -> track_id lookups.
    Thread-safe for concurrent access.
    """
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()

    def get(self, artist: str, title: str) -> Optional[str]:
        """
        Look up a track_id for the given artist and title.
        Returns the track_id if found, else None.
        """
        with self._lock, closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                'SELECT track_id FROM track_cache WHERE artist=? AND title=?',
                (artist.casefold(), title.casefold())
            )
            row = cur.fetchone()
            return row[0] if row else None

    def set(self, artist: str, title: str, track_id: str) -> None:
        """
        Store a track_id for the given artist and title.
        """
        with self._lock, closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO track_cache (artist, title, track_id) VALUES (?, ?, ?)',
                (artist.casefold(), title.casefold(), track_id)
            )
            conn.commit()
