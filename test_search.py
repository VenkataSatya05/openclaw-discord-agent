import requests
import re

query = "top 10 athletes of all time"
encoded = requests.utils.quote(query)

print("=" * 50)
print("TEST 1: DDG Instant Answer API")
print("=" * 50)
try:
    res = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    ).json()
    print(f"AbstractText: {res.get('AbstractText', 'EMPTY')}")
    print(f"RelatedTopics count: {len(res.get('RelatedTopics', []))}")
    print(f"First topic: {res.get('RelatedTopics', [{}])[0]}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 50)
print("TEST 2: DDG HTML scrape")
print("=" * 50)
try:
    res = requests.get(
        f"https://html.duckduckgo.com/html/?q={encoded}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=15,
    )
    print(f"Status: {res.status_code}")
    print(f"Response length: {len(res.text)}")
    print(f"First 500 chars:\n{res.text[:500]}")
    titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', res.text, re.DOTALL)
    print(f"Titles found: {titles[:3]}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 50)
print("TEST 3: Wikipedia Search")
print("=" * 50)
try:
    res = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 3},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    ).json()
    for r in res.get("query", {}).get("search", []):
        print(f"Title: {r['title']}")
        print(f"Snippet: {re.sub(r'<.*?>', '', r.get('snippet', ''))[:100]}")
        print()
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 50)
print("TEST 4: Direct internet connectivity")
print("=" * 50)
try:
    res = requests.get("https://httpbin.org/get", timeout=5)
    print(f"Status: {res.status_code} — Internet works ✅")
except Exception as e:
    print(f"ERROR: {e} — NO INTERNET ❌")