"""Extract weighted topic vectors and classify into categories."""
import re
from collections import Counter

STOP_WORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with','by',
    'is','are','was','were','be','been','being','have','has','had','do','does',
    'did','will','would','could','should','may','might','can','this','that',
    'these','those','you','your','i','we','our','they','them','it','its','as',
    'from','if','then','than','so','not','no','yes','all','any','some','more'
}

CATEGORY_KEYWORDS = {
    'machine_learning': ['machine','learning','ai','neural','model','training',
                         'dataset','pytorch','tensorflow','llm','transformer','gpt'],
    'web_development':  ['web','html','css','javascript','react','vue','frontend',
                         'backend','node','express','next','typescript','api'],
    'devops':           ['devops','docker','kubernetes','cloud','deploy','ci',
                         'cd','terraform','ansible','aws','gcp','azure','pipeline'],
    'saas':             ['saas','subscription','platform','billing','stripe',
                         'multi-tenant','dashboard','onboarding','freemium'],
    'cybersecurity':    ['security','vulnerability','penetration','exploit','malware',
                         'firewall','encryption','auth','oauth','jwt','infosec'],
    'adtech':           ['adtech','advertising','programmatic','rtb','dsp','ssp',
                         'impression','click','campaign','adserver','cpm'],
    'general':          ['software','code','developer','programming','opensource']
}

def extract_topic_vector(text: str, top_n: int = 30) -> dict:
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
    if not words:
        return {}
    freq = Counter(words)
    total = sum(freq.values())
    return {w: c / total for w, c in freq.most_common(top_n)}

def analyze_github_repo(repo_content: str) -> dict:
    return extract_topic_vector(repo_content, top_n=40)

def classify_topic(topic_vector: dict) -> str:
    scores = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(topic_vector.get(k, 0.0) for k in kws)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'general'

def compute_relevance(topic_vector: dict, community_text: str) -> float:
    tokens = set(re.sub(r'[^a-zA-Z0-9\s]', ' ', community_text.lower()).split())
    if not tokens:
        return 0.0
    total_weight = sum(topic_vector.values())
    if total_weight == 0:
        return 0.0
    matched = sum(w for k, w in topic_vector.items() if k in tokens)
    return round((matched / total_weight) * 100, 1)