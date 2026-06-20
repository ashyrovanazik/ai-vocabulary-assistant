import os
import re
import requests
from urllib.parse import urlparse

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
TAVILY_ENDPOINT = os.getenv('TAVILY_ENDPOINT', 'https://api.tavily.com/search')


def detect_source_name(url):
    try:
        host = urlparse(url).netloc.lower()
        if 'reuters.com' in host:
            return 'Reuters'
        if 'bbc.co' in host or 'bbc.com' in host:
            return 'BBC'
        if 'apnews' in host or 'ap.org' in host:
            return 'AP News'
        if 'theguardian' in host or 'guardian.co' in host:
            return 'The Guardian'
        if 'npr.org' in host:
            return 'NPR'
        if 'nytimes.com' in host:
            return 'The New York Times'
        # fallback to domain as a safe non-fabricated name
        return host
    except Exception:
        return None


def extract_sentence_containing_word(text, word):
    if not text:
        return None
    pattern = re.compile(r'([^.?!]*\b' + re.escape(word) + r"\b[^.?!]*[.?!])", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    # fallback: return a short excerpt if exact sentence not found
    idx = text.lower().find(word.lower())
    if idx >= 0:
        start = max(0, idx - 80)
        end = min(len(text), idx + 80)
        return text[start:end].strip()
    return None


def search_word_sources(word, prefer_sources=None, max_results=10):
    """Search for the word using Tavily and return the first authentic source with an example sentence.

    Returns dict with keys: source_name, source_url, example_sentence
    or None if not found.
    """
    if not TAVILY_API_KEY:
        raise RuntimeError('Missing TAVILY_API_KEY')

    query = f"{word} English news"
    if prefer_sources:
        query += ' ' + ' '.join(prefer_sources)

    headers = {
        'Content-Type': 'application/json'
        }
    payload = { 
        'api_key': TAVILY_API_KEY,
        'query': query,
        'search_depth': 'basic',
        'max_results': max_results
    }
    
    try:
        resp = requests.post(TAVILY_ENDPOINT, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f'Tavily API error: {e}')

    # Attempt to read hits from common structures
    hits = []
    if isinstance(data, dict):
        # common field names: hits, results, data
        for key in ('hits', 'results', 'data'):
            if key in data and isinstance(data[key], list):
                hits = data[key]
                break
    if not hits and isinstance(data, list):
        hits = data

    # normalize candidate items
    candidates = []
    for item in hits:
        url = None
        text = None
        if isinstance(item, dict):
            url = item.get('url') or item.get('link') or item.get('source')
            text = item.get('content') or item.get('snippet') or item.get('text')
        elif isinstance(item, str):
            url = item
        if url:
            candidates.append({'url': url, 'text': text})

    # prioritize preferred domains
    prefer_sources = prefer_sources or ['Reuters', 'BBC', 'AP News', 'The Guardian', 'NPR', 'The New York Times']

    # first pass: try preferred sources
    for pref in prefer_sources:
        for c in candidates:
            try:
                name = detect_source_name(c['url'])
            except Exception:
                name = None
            if name and pref.lower() in str(name).lower():
                example = extract_sentence_containing_word(c.get('text') or fetch_url_text(c['url']), word)
                if example:
                    return {'source_name': name, 'source_url': c['url'], 'example_sentence': example}

    # second pass: any candidate that contains the word
    for c in candidates:
        text = c.get('text') or fetch_url_text(c['url'])
        example = extract_sentence_containing_word(text, word)
        if example:
            name = detect_source_name(c['url'])
            return {'source_name': name, 'source_url': c['url'], 'example_sentence': example}

    return None


def fetch_url_text(url):
    """Fetch a page and try to extract readable text snippet (best-effort)."""
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        # crude: return visible text by stripping tags (simple)
        text = re.sub('<[^<]+?>', ' ', resp.text)
        text = re.sub('\s+', ' ', text)
        return text
    except Exception:
        return ''
