"""Find each subreddit's peak activity hours (best time to post)."""
from datetime import datetime, timedelta

class TimingOptimizer:
    def __init__(self, reddit_client):
        self.reddit = reddit_client
        self.cache = {}

    def profile_subreddit(self, subreddit_name: str, sample_size: int = 50) -> dict:
        if subreddit_name in self.cache:
            return self.cache[subreddit_name]
        try:
            sub = self.reddit.subreddit(subreddit_name)
            hourly = {h: [] for h in range(24)}
            for post in sub.hot(limit=sample_size):
                h = datetime.utcfromtimestamp(post.created_utc).hour
                hourly[h].append(post.score)
            profile = {h: (sum(v)/len(v) if v else 0) for h, v in hourly.items()}
            self.cache[subreddit_name] = profile
            return profile
        except Exception:
            return {h: 0 for h in range(24)}

    def best_hours(self, subreddit_name: str, top_n: int = 3) -> list:
        profile = self.profile_subreddit(subreddit_name)
        ranked = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        return [h for h, _ in ranked[:top_n]]

    def next_safe_slot(self, subreddit_name: str, min_gap_minutes: int) -> datetime:
        now = datetime.utcnow()
        peaks = self.best_hours(subreddit_name, top_n=3)
        candidate = now + timedelta(minutes=min_gap_minutes)
        for _ in range(48):
            if candidate.hour in peaks:
                return candidate
            candidate += timedelta(minutes=30)
        return candidate