"""Pre-flight ban-risk checks: karma, ratio, shadowban, sentiment."""
import time
import requests

class SafetyGuard:
    def __init__(self, reddit_client, limits: dict):
        self.reddit = reddit_client
        self.limits = limits
        self._last_check = {}

    def get_karma(self):
        try:
            me = self.reddit.user.me()
            return (me.link_karma or 0) + (me.comment_karma or 0)
        except Exception:
            return 0

    def check_self_promo_ratio(self, subreddit_name: str) -> bool:
        try:
            user = self.reddit.user.me()
            recent = list(user.submissions.new(limit=20))
            promo = sum(1 for s in recent
                        if s.subreddit.display_name.lower() == subreddit_name.lower()
                        and s.is_self is False)
            if not recent:
                return True
            ratio = promo / len(recent)
            return ratio <= self.limits['reddit']['max_self_promo_ratio']
        except Exception:
            return True

    def is_shadowbanned(self, username: str) -> bool:
        cache_key = f"sb_{username}"
        if cache_key in self._last_check and time.time() - self._last_check[cache_key] < 3600:
            return False
        self._last_check[cache_key] = time.time()
        try:
            url = f"https://www.reddit.com/user/{username}/about.json"
            headers = {'User-Agent': 'LinkForgeStudio/5.0'}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 404:
                return True
            data = r.json()
            return not data.get('data', {}).get('is_employee') is None and data.get('data', {}).get('name') is None
        except Exception:
            return False

    def subreddit_allows_promo(self, subreddit_name: str) -> tuple:
        try:
            sub = self.reddit.subreddit(subreddit_name)
            for rule in sub.rules():
                rl = (rule.short_name or '').lower()
                if any(bad in rl for bad in ['no self-promotion', 'no advertising',
                                              'no spam', 'no promotion', 'no links']):
                    return False, rule.short_name
            return True, 'ok'
        except Exception as e:
            return False, f'rule_fetch_failed: {e}'

    def check_sentiment(self, subreddit_name: str) -> bool:
        try:
            sub = self.reddit.subreddit(subreddit_name)
            hot = list(sub.hot(limit=5))
            if not hot:
                return True
            negative = sum(1 for p in hot if p.score < 0)
            return negative < 3
        except Exception:
            return True

    def warmup_multiplier(self, account_age_days: int, warmup_days: int) -> float:
        if account_age_days >= warmup_days:
            return 1.0
        return max(0.2, account_age_days / warmup_days)