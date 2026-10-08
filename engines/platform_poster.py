"""Multi-platform posting with dedup, delays, and safety gates."""
import hashlib, json, random, time
from datetime import datetime, timezone

class PlatformPoster:
    def __init__(self, limits, ai_gen):
        self.limits = limits
        self.ai = ai_gen
        self.history = []

    def _fp(self, url, title):
        return hashlib.md5(f"{url}|{title}".encode()).hexdigest()

    def _dup(self, fp, platform, window_h=24):
        cutoff = time.time() - window_h * 3600
        return any(h['fp'] == fp and h['platform'] == platform
                   and h['ts'] > cutoff for h in self.history)

    def reddit_post(self, reddit, sub, title, url, tracker_url, seed_comment=True):
        fp = self._fp(url, title)
        if self._dup(fp, 'reddit'):
            return False, f"Duplicate post for r/{sub}"
        try:
            s = reddit.subreddit(sub).submit(title=title, url=tracker_url,
                                             send_replies=False)
            if seed_comment:
                try:
                    comment = self.ai.generate_comment(title.split()[-1])
                    time.sleep(3)
                    s.reply(comment)
                except Exception:
                    pass
            self.history.append({'platform':'reddit','fp':fp,'ts':time.time()})
            wait_min = (self.limits['reddit']['min_interval_minutes']
                        + random.uniform(0, self.limits['reddit']['jitter_minutes']))
            if not self.limits['global']['enable_dry_run']:
                time.sleep(wait_min * 60)
            return True, s.permalink
        except Exception as e:
            time.sleep(5)
            return False, str(e)

    def daily_count(self, platform):
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).timestamp()
        return sum(1 for h in self.history if h['platform'] == platform and h['ts'] >= today)