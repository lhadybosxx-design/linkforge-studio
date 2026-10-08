"""A/B test variants per link — track which performs best."""
import sqlite3
import json
import os
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics.db')

class ContentRotator:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS variants
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      link TEXT, variant TEXT, title TEXT,
                      impressions INTEGER DEFAULT 0,
                      clicks INTEGER DEFAULT 0,
                      created_at TEXT)''')
        conn.commit()
        conn.close()

    def register_variant(self, link: str, variant: str, title: str):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO variants (link, variant, title, created_at) VALUES (?, ?, ?, ?)',
                  (link, variant, title, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    def record_click(self, link: str, variant: str = None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('UPDATE variants SET clicks = clicks + 1 WHERE link = ?', (link,))
        conn.commit()
        conn.close()

    def record_impression(self, link: str, variant: str = None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('UPDATE variants SET impressions = impressions + 1 WHERE link = ?', (link,))
        conn.commit()
        conn.close()

    def best_variant(self, link: str) -> dict:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''SELECT variant, title, clicks, impressions,
                            CAST(clicks AS FLOAT) / MAX(impressions, 1) AS ctr
                     FROM variants WHERE link = ?
                     ORDER BY ctr DESC LIMIT 1''', (link,))
        row = c.fetchone()
        conn.close()
        if not row:
            return {}
        return {'variant': row[0], 'title': row[1], 'clicks': row[2],
                'impressions': row[3], 'ctr': round(row[4], 4)}