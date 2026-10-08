"""Score communities by topical relevance; enforce rule safety."""
import json, time, os
from engines.topic_analyzer import compute_relevance
from engines.safety_guard import SafetyGuard

class CommunityMatcher:
    def __init__(self, reddit_client, limits, targeting_path=None):
        if targeting_path is None:
            targeting_path = os.path.join(os.path.dirname(__file__),
                                          '..', 'config', 'targeting_rules.json')
        with open(targeting_path) as f:
            self.rules = json.load(f)
        self.reddit = reddit_client
        self.guard = SafetyGuard(reddit_client, limits)
        self.cache = {}

    def _info(self, name):
        if name in self.cache:
            return self.cache[name]
        try:
            sub = self.reddit.subreddit(name)
            info = {
                'name': name,
                'description': (sub.public_description or '') + ' ' + (sub.title or ''),
                'subscribers': sub.subscribers,
                'active_users': sub.active_user_count,
                'over18': sub.over18
            }
            time.sleep(0.7)
            self.cache[name] = info
            return info
        except Exception:
            return None

    def score(self, topic_vector, name):
        info = self._info(name)
        if not info or info['over18'] or info['subscribers'] < 1000:
            return 0, 'filtered'
        ok, reason = self.guard.subreddit_allows_promo(name)
        if not ok:
            return 0, reason
        if not self.guard.check_sentiment(name):
            return 0, 'negative_sentiment'
        rel = compute_relevance(topic_vector, info['description'])
        if info['active_users'] > 100:
            rel += 5
        return min(rel, 100), 'ok'

    def find_best(self, topic_vector, category, min_score=70, top_n=10):
        candidates = list(self.rules['topic_to_communities']
                          .get(category, {}).get('reddit', []))
        candidates += self.rules['topic_to_communities']['general']['reddit']
        results = []
        for c in set(candidates):
            s, reason = self.score(topic_vector, c)
            if s >= min_score:
                results.append({'community': c, 'score': s, 'reason': reason})
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]