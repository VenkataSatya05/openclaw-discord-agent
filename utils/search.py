"""
utils/search.py — Two-stage web search: Wikipedia first, Bing as fallback.

Usage:
    from utils.search import search_web

    result = await search_web("IPL 2024 winner")
"""

import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Keywords that suggest a list/ranking query → pull full Wikipedia extract
LIST_KEYWORDS = [
    "top", "best", "greatest", "list", "ranking", "all time",
    "richest", "largest", "most", "famous", "history",
    "winners", "world cup", "champion",
]


# ── Wikipedia helpers ──────────────────────────────────────────────────────────

def _wiki_search(query: str) -> list[dict]:
    """Return up to 6 Wikipedia search result snippets."""
    try:
        data = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action":  "query",
                "list":    "search",
                "srsearch": query,
                "format":  "json",
                "srlimit": 6,
            },
            headers=HEADERS,
            timeout=10,
        ).json()
        return [
            {
                "title":   r["title"],
                "snippet": re.sub(r"<.*?>", "", r.get("snippet", "")),
            }
            for r in data.get("query", {}).get("search", [])
        ]
    except Exception as e:
        print(f"  [Wikipedia search] {e}")
        return []


def _wiki_summary(title: str) -> str:
    """Return the REST summary extract for a Wikipedia page."""
    try:
        data = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/"
            f"{requests.utils.quote(title.replace(' ', '_'))}",
            headers=HEADERS,
            timeout=10,
        ).json()
        return data.get("extract", "")
    except Exception as e:
        print(f"  [Wikipedia summary] {e}")
        return ""


def _wiki_extract(title: str) -> str:
    """Return the full intro-section plain-text extract for a Wikipedia page."""
    try:
        data = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action":     "query",
                "titles":     title,
                "prop":       "extracts",
                "exintro":    True,
                "explaintext": True,
                "format":     "json",
            },
            headers=HEADERS,
            timeout=10,
        ).json()
        for page in data.get("query", {}).get("pages", {}).values():
            return page.get("extract", "")
    except Exception as e:
        print(f"  [Wikipedia extract] {e}")
    return ""


# ── Bing fallback ──────────────────────────────────────────────────────────────

def _bing_search(query: str) -> list[dict]:
    """Scrape Bing results as a fallback when Wikipedia returns nothing."""
    try:
        res = requests.get(
            f"https://www.bing.com/search?q={requests.utils.quote(query)}&cc=IN",
            headers={
                "User-Agent":      (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
        )
        titles   = re.findall(r"<h2><a[^>]*>(.*?)</a></h2>", res.text, re.DOTALL)
        snippets = re.findall(r'<div class="b_caption"><p>(.*?)</p>', res.text, re.DOTALL)
        titles   = [re.sub(r"<.*?>", "", t).strip() for t in titles]
        snippets = [re.sub(r"<.*?>", "", s).strip() for s in snippets]

        results = []
        for i in range(min(len(titles), len(snippets), 5)):
            if titles[i]:
                results.append({"title": titles[i], "snippet": snippets[i]})
        return results
    except Exception as e:
        print(f"  [Bing search] {e}")
        return []


# ── Public entry point ─────────────────────────────────────────────────────────

async def search_web(query: str) -> str:
    """
    Search the web for *query* and return a formatted Discord-ready string.

    Tries Wikipedia first; falls back to Bing if no results.
    Returns the sentinel string ``"SEARCH_FAILED"`` when both fail.
    """
    print(f"  🌐 Searching: '{query}'")
    results: list[dict] = []
    source = ""

    # ── Wikipedia ──
    wiki_results = _wiki_search(query)
    if wiki_results:
        results = wiki_results
        source  = "Wikipedia"

        # Prefer longer REST summary over raw snippet
        summary = _wiki_summary(results[0]["title"])
        if summary:
            results[0]["snippet"] = summary

        # For list/ranking queries pull the full intro extract
        if any(kw in query.lower() for kw in LIST_KEYWORDS):
            extract = _wiki_extract(results[0]["title"])
            if extract and len(extract) > len(results[0]["snippet"]):
                results[0]["snippet"] = extract[:1500]

    # ── Bing fallback ──
    if not results:
        bing_results = _bing_search(query)
        if bing_results:
            results = bing_results
            source  = "Bing"

    if not results:
        return "SEARCH_FAILED"

    out = f"🔍 **Results for:** {query}\n_(via {source})_\n\n"
    for i, r in enumerate(results[:5], 1):
        title   = r.get("title", "").strip()
        snippet = r.get("snippet", "").strip()
        if title or snippet:
            out += f"**{i}. {title}**\n{snippet}\n\n"
    return out.strip()