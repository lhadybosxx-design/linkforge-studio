"""LinkForge Studio — Local Flask App (UI + API + Tracker)."""
import base64, json, os, random, subprocess, sys, threading, time, uuid
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))
from engines.topic_analyzer import analyze_github_repo, classify_topic
from engines.ai_title_gen import TitleGenerator
from engines.safety_guard import SafetyGuard
from engines.community_matcher import CommunityMatcher
from engines.platform_poster import PlatformPoster
from engines.timing_optimizer import TimingOptimizer
from engines.content_rotator import ContentRotator
from engines.analytics_engine import (init_db, log_post, log_event,
                                       register_link, get_real_url,
                                       summary, recent_posts)

# ---------- App ----------
app = Flask(__name__, template_folder='templates', static_folder='static')
init_db()

PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

# ---------- Config ----------
ROOT = os.path.dirname(os.path.abspath(__file__))

def load_config(name):
    with open(os.path.join(ROOT, 'config', name), encoding='utf-8') as f:
        return json.load(f)

LIMITS = load_config('safety_limits.json')
PLATFORMS = load_config('platforms.json')

# ---------- Helpers ----------
def clone_repo(url: str) -> str:
    name = url.rstrip('/').split('/')[-1].replace('.git', '')
    target = os.path.join(ROOT, 'repos', name)
    if not os.path.exists(target):
        os.makedirs(os.path.join(ROOT, 'repos'), exist_ok=True)
        try:
            subprocess.run(["git", "clone", "--depth", "1", url, target],
                           check=True, capture_output=True, timeout=120)
        except Exception as e:
            return f"Failed to clone: {e}"
    readme = os.path.join(target, 'README.md')
    if os.path.exists(readme):
        with open(readme, encoding='utf-8', errors='ignore') as f:
            return f.read()
    return name.replace('-', ' ').replace('_', ' ')

def make_links(base_url, keywords, n):
    links = []
    for i in range(n):
        utm = {
            "utm_source": random.choice(["reddit", "twitter", "linkedin"]),
            "utm_medium": random.choice(["social", "cpc", "organic"]),
            "utm_campaign": random.choice(["launch", "promo", "update"]),
            "utm_content": f"v{i+1}_{int(time.time())}",
            "utm_term": random.choice(keywords).strip()
        }
        qs = "&".join(f"{k}={v}" for k, v in utm.items())
        links.append(f"{base_url}?{qs}")
    return links

def init_reddit():
    try:
        import praw
        acct = PLATFORMS['reddit']['accounts'][0]
        return praw.Reddit(
            client_id=acct['client_id'],
            client_secret=acct['client_secret'],
            username=acct['username'],
            password=acct['password'],
            user_agent=acct['user_agent']
        )
    except Exception as e:
        print(f"[!] Reddit init failed: {e}")
        return None

# ---------- UI Routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    stats = summary()
    posts = recent_posts(limit=50)
    return render_template('dashboard.html', stats=stats, posts=posts,
                           updated=datetime.utcnow().isoformat())

# ---------- Tracker Routes ----------
@app.route('/r/<tid>')
def redirect_tracked(tid):
    log_event(tid, 'click',
              request.remote_addr,
              request.headers.get('User-Agent', ''),
              request.headers.get('Referer', ''))
    real = get_real_url(tid)
    if not real:
        return "Unknown tracker ID", 404
    return redirect(real, code=302)

@app.route('/pixel/<tid>.gif')
def pixel(tid):
    log_event(tid, 'impression',
              request.remote_addr,
              request.headers.get('User-Agent', ''))
    return PIXEL, 200, {'Content-Type': 'image/gif',
                        'Cache-Control': 'no-store,no-cache,must-revalidate'}

# ---------- API Routes ----------
@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})

@app.route('/api/analyze-repo', methods=['POST'])
def api_analyze_repo():
    data = request.get_json() or {}
    repo_url = data.get('repo_url', '').strip()
    if not repo_url:
        return jsonify({'error': 'repo_url required'}), 400
    content = clone_repo(repo_url)
    vector = analyze_github_repo(content)
    category = classify_topic(vector)
    return jsonify({
        'category': category,
        'top_keywords': list(vector.keys())[:15],
        'vector': vector
    })

@app.route('/api/generate-links', methods=['POST'])
def api_generate_links():
    data = request.get_json() or {}
    base_url = data.get('base_url', '').strip()
    keywords = data.get('keywords', [])
    n = int(data.get('num_links', 10))
    if not base_url or not keywords:
        return jsonify({'error': 'base_url and keywords required'}), 400
    links = make_links(base_url, keywords, n)
    # Register each link with the local tracker
    out = []
    for link in links:
        tid = uuid.uuid4().hex[:12]
        register_link(tid, link)
        tracker_url = f"{PLATFORMS['tracker']['base_url']}/r/{tid}"
        out.append({'real_url': link, 'tracker_url': tracker_url, 'tracker_id': tid})
    return jsonify({'links': out, 'count': len(out)})

@app.route('/api/find-communities', methods=['POST'])
def api_find_communities():
    data = request.get_json() or {}
    repo_url = data.get('repo_url', '')
    keywords = data.get('keywords', [])
    content = clone_repo(repo_url) if repo_url else ''
    vector = analyze_github_repo(content + " " + " ".join(keywords))
    category = classify_topic(vector)

    reddit = init_reddit()
    if not reddit:
        return jsonify({'error': 'Reddit not configured. Edit config/platforms.json'} ), 400

    try:
        matcher = CommunityMatcher(reddit, LIMITS)
        communities = matcher.find_best(
            vector, category,
            min_score=LIMITS['global']['relevance_score_threshold'])
        return jsonify({'category': category, 'communities': communities})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/post', methods=['POST'])
def api_post():
    data = request.get_json() or {}
    links = data.get('links', [])
    communities = data.get('communities', [])
    dry_run = bool(data.get('dry_run', LIMITS['global']['enable_dry_run']))

    if not links or not communities:
        return jsonify({'error': 'links and communities required'}), 400

    reddit = init_reddit()
    if not reddit:
        return jsonify({'error': 'Reddit not configured'}), 400

    # Run in background thread
    def _worker():
        guard = SafetyGuard(reddit, LIMITS)
        titles = TitleGenerator()
        poster = PlatformPoster(LIMITS, titles)
        rotator = ContentRotator()

        try:
            me = reddit.user.me()
            if guard.is_shadowbanned(me.name):
                print("[!] SHADOWBANNED — aborting")
                return
        except Exception:
            pass

        posted = 0
        max_posts = LIMITS['reddit']['max_posts_per_day']

        for link_obj in links:
            if posted >= max_posts:
                break
            tracker_url = link_obj.get('tracker_url')
            real_url = link_obj.get('real_url')
            tracker_id = link_obj.get('tracker_id')

            for sub in communities:
                if posted >= max_posts:
                    break
                if poster.daily_count('reddit') >= max_posts:
                    break
                if not guard.check_self_promo_ratio(sub):
                    print(f"[!] 90/10 ratio block for r/{sub}")
                    continue

                title = titles.generate("project", "project", 1)[0]
                rotator.register_variant(real_url, tracker_id, title)

                if dry_run:
                    print(f"[DRY-RUN] would post to r/{sub}: {title}")
                    log_post('reddit', sub, real_url, tracker_id, title, 'dry_run')
                    posted += 1
                    continue

                ok, msg = poster.reddit_post(reddit, sub, title, real_url,
                                             tracker_url, seed_comment=True)
                log_post('reddit', sub, real_url, tracker_id, title,
                         'success' if ok else f'failed: {msg}')
                if ok:
                    posted += 1
                    print(f"[OK] r/{sub} → {msg}")

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({'status': 'started', 'links': len(links),
                    'communities': len(communities), 'dry_run': dry_run})

@app.route('/api/stats')
def api_stats():
    return jsonify(summary())

@app.route('/api/posts')
def api_posts():
    rows = recent_posts(limit=int(request.args.get('limit', 50)))
    return jsonify({'posts': [list(r) for r in rows]})

# ---------- Main ----------
if __name__ == '__main__':
    print("=" * 60)
    print("  🚀 LinkForge Studio — Local Edition")
    print("=" * 60)
    print(f"  Control Panel →  http://localhost:{LIMITS['global']['local_port']}/")
    print(f"  Dashboard     →  http://localhost:{LIMITS['global']['local_port']}/dashboard")
    print("=" * 60)
    app.run(host='127.0.0.1', port=LIMITS['global']['local_port'], debug=False)