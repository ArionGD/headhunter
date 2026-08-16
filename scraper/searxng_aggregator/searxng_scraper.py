import requests
import urllib.parse
import re

SEARXNG_NODES = [
    "https://searx.be",
    "https://searxng.site",
    "https://searx.prvcy.eu"
]

def search_searxng_aggregator(query: str, max_results: int = 5):
    """
    Keyless SearXNG multi-engine aggregator querying 70+ search engines simultaneously.
    """
    print(f"Executing SearXNG Multi-Engine query: {query[:80]}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 HeadHunt/2.0"
    }

    results = []
    for node in SEARXNG_NODES:
        url = f"{node}/search?q={urllib.parse.quote(query)}&format=json"
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results", [])
                for item in raw_results:
                    link = item.get("url", "")
                    if "linkedin.com/in/" in link:
                        results.append({
                            "url": link,
                            "title_raw": item.get("title", ""),
                            "snippet": item.get("content", "")
                        })
                        if len(results) >= max_results:
                            break
                if results:
                    break
        except Exception as e:
            print(f"SearXNG node {node} notice: {e}")
            continue

    return results

def parse_searxng_result(item: dict, target_location: str = "Chennai"):
    raw_title = item.get("title_raw", "")
    snippet = item.get("snippet", "")
    url = item.get("url", "")

    cleaned_title = re.sub(r'\s*\|\s*LinkedIn.*$', '', raw_title, flags=re.IGNORECASE)
    parts = [p.strip() for p in cleaned_title.split('-') if p.strip()]

    name = parts[0] if parts else "Aggregated Lead"
    title = parts[1] if len(parts) > 1 else "Corporate Professional"
    org = parts[2] if len(parts) > 2 else "Enterprise"

    return {
        "name": name,
        "title": title,
        "organization": org,
        "email": "",
        "location": f"{target_location}, Tamil Nadu",
        "linkedin_url": url,
        "notes": f"SearXNG Aggregated Match: {snippet[:250]}",
        "source": "searxng_aggregator",
        "status": "discovered"
    }
