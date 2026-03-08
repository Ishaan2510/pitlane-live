from flask import Blueprint, jsonify
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import time
import re

bp = Blueprint('news', __name__, url_prefix='/api')

# Simple in-memory cache — refresh every 10 minutes
_cache = {'data': [], 'ts': 0}
CACHE_TTL = 600  # seconds

AUTOSPORT_RSS = 'https://www.autosport.com/rss/f1/news/'


def _time_ago(pub_date_str: str) -> str:
    """Convert RSS pubDate to '2h ago' style string."""
    try:
        # RSS date format: "Mon, 08 Mar 2026 10:30:00 +0000"
        dt = datetime.strptime(pub_date_str.strip(), '%a, %d %b %Y %H:%M:%S %z')
        now = datetime.now(timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 3600:
            return f'{diff // 60}m ago'
        if diff < 86400:
            return f'{diff // 3600}h ago'
        return f'{diff // 86400}d ago'
    except Exception:
        return ''


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r'<[^>]+>', '', text or '')
    text = text.replace('&amp;', '&').replace('&lt;', '<') \
               .replace('&gt;', '>').replace('&quot;', '"') \
               .replace('&#39;', "'").replace('&nbsp;', ' ')
    return text.strip()


def _category_from_title(title: str) -> str:
    """Infer a display category from the headline."""
    title_lower = title.lower()
    if any(w in title_lower for w in ['race result', 'wins', 'victory', 'podium', 'grand prix']):
        return 'RACE'
    if any(w in title_lower for w in ['qualifying', 'pole', 'grid']):
        return 'QUALIFYING'
    if any(w in title_lower for w in ['technical', 'car', 'upgrade', 'regulation', 'engine']):
        return 'TECHNICAL'
    if any(w in title_lower for w in ['transfer', 'contract', 'signing', 'seat', 'driver market']):
        return 'PADDOCK'
    if any(w in title_lower for w in ['practice', 'fp1', 'fp2', 'fp3', 'testing']):
        return 'PRACTICE'
    return 'F1'


def _fetch_news():
    """Fetch and parse Autosport RSS, return list of article dicts."""
    try:
        resp = requests.get(AUTOSPORT_RSS, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (PitLane Live/1.0)'
        })
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find('channel')
        items = []

        for item in (channel.findall('item') if channel else [])[:12]:
            title   = _strip_html(item.findtext('title', ''))
            link    = item.findtext('link', '')
            pub     = item.findtext('pubDate', '')
            desc    = _strip_html(item.findtext('description', ''))

            # Truncate summary to ~180 chars at a word boundary
            if len(desc) > 180:
                desc = desc[:177].rsplit(' ', 1)[0] + '…'

            if title and link:
                items.append({
                    'title':    title,
                    'link':     link,
                    'time':     _time_ago(pub),
                    'summary':  desc,
                    'category': _category_from_title(title),
                })

        return items

    except Exception as e:
        print(f'[news] RSS fetch error: {e}')
        return []


@bp.route('/news', methods=['GET'])
def get_news():
    """
    Return latest F1 news from Autosport RSS.
    Cached for 10 minutes to avoid hammering the RSS feed.
    """
    global _cache
    now = time.time()

    if now - _cache['ts'] > CACHE_TTL or not _cache['data']:
        fresh = _fetch_news()
        if fresh:
            _cache = {'data': fresh, 'ts': now}

    if not _cache['data']:
        return jsonify({'error': 'Could not load news'}), 503

    return jsonify(_cache['data'])