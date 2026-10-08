"""Generate unique, non-repeating titles using template + synonym rotation."""
import json
import random
import hashlib
import os

class TitleGenerator:
    def __init__(self, templates_path=None):
        if templates_path is None:
            templates_path = os.path.join(os.path.dirname(__file__),
                                          '..', 'config', 'ai_templates.json')
        with open(templates_path, encoding='utf-8') as f:
            data = json.load(f)
        self.templates = data['templates']
        self.synonyms = data['synonyms']
        self.comment_seeds = data['comment_seed_templates']
        self._seen = set()

    def _sub_synonyms(self, text: str) -> str:
        for word, alts in self.synonyms.items():
            if word in text:
                text = text.replace(word, random.choice(alts), 1)
        return text

    def generate(self, topic: str, keyword: str, n: int = 1) -> list:
        results = []
        attempts = 0
        while len(results) < n and attempts < n * 20:
            attempts += 1
            tpl = random.choice(self.templates)
            title = tpl.format(topic=topic, keyword=keyword,
                               n=random.choice([2, 3, 4, 6, 8, 12]))
            title = self._sub_synonyms(title)
            fp = hashlib.md5(title.encode()).hexdigest()
            if fp in self._seen:
                continue
            self._seen.add(fp)
            results.append(title)
        return results

    def generate_comment(self, keyword: str) -> str:
        tpl = random.choice(self.comment_seeds)
        return tpl.format(keyword=keyword)