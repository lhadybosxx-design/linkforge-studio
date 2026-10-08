"""SQLite analytics store for posts, clicks, impressions."""
import sqlite3, os
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics.db')

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT, community TEXT, link TEXT, tracker_id TEXT,
        title TEXT, posted_at TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracker_id TEXT, event_type TEXT, timestamp TEXT,
        ip TEXT, user_agent TEXT, referer TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracker_id TEXT UNIQUE, real_url TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

def log_post(platform, community, link, tracker_id, title, status='success'):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''INSERT INTO posts
                 (platform, community, link, tracker_id, title, posted_at, status)
                 VALUES (?,?,?,?,?,?,?)''',
              (platform, community, link, tracker_id, title,
               datetime.utcnow().isoformat(), status))
    conn.commit(); conn.close()

def log_event(tracker_id, event_type, ip='', ua='', referer=''):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''INSERT INTO events (tracker_id, event_type, timestamp, ip, user_agent, referer)
                 VALUES (?,?,?,?,?,?)''',
              (tracker_id, event_type, datetime.utcnow().isoformat(), ip, ua, referer))
    conn.commit(); conn.close()

def register_link(tracker_id, real_url):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO links (tracker_id, real_url, created_at) VALUES (?,?,?)',
              (tracker_id, real_url, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def get_real_url(tracker_id):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT real_url FROM links WHERE tracker_id = ?', (tracker_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def summary():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts"); posts = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='click'"); clicks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='impression'"); imps = c.fetchone()[0]
    conn.close()
    return {'posts': posts, 'clicks': clicks, 'impressions': imps,
            'ctr': round(clicks/max(imps,1)*100, 2)}

def recent_posts(limit=50):
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('''SELECT p.id, p.platform, p.community, p.title, p.posted_at,
                        (SELECT COUNT(*) FROM events WHERE tracker_id = p.tracker_id AND event_type='click') as clicks,
                        (SELECT COUNT(*) FROM events WHERE tracker_id = p.tracker_id AND event_type='impression') as imps
                 FROM posts p ORDER BY p.id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows