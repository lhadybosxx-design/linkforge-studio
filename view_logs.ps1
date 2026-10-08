Set-Location $PSScriptRoot
python -c @"
import sqlite3
conn = sqlite3.connect('data/analytics.db')
c = conn.cursor()
print('=== Recent Posts ===')
for r in c.execute('SELECT platform, community, title, posted_at, status FROM posts ORDER BY id DESC LIMIT 20'):
    print(r)
print()
print('=== Event Counts ===')
for r in c.execute('SELECT event_type, COUNT(*) FROM events GROUP BY event_type'):
    print(r)
print()
print('=== Top Links by Clicks ===')
for r in c.execute('''SELECT tracker_id, COUNT(*) FROM events
                      WHERE event_type='click' GROUP BY tracker_id
                      ORDER BY COUNT(*) DESC LIMIT 10'''):
    print(r)
"@