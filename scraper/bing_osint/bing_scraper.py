import re
import urllib.parse
import requests

def search_bing_osint(query: str, max_results: int = 5):
    """
    Keyless Bing OSINT search engine querying Bing's web index for LinkedIn profiles.
    """
    print(f"Executing Bing OSINT query: {query[:80]}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 HeadHunt/2.0"
    }
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    results = []

    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            html = response.text
            # Extract links and snippets from Bing search results
            matches = re.findall(r'<li class="b_algo">.*?<a href="(https://[a-z]{2,3}\.linkedin\.com/in/[^"]+)".*?h2>.*?<a[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>', html, re.DOTALL)
            
            for link, title_raw, snippet_raw in matches:
                clean_title = re.sub(r'<[^>]+>', '', title_raw).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()
                results.append({
                    "url": link,
                    "title_raw": clean_title,
                    "snippet": clean_snippet
                })
                if len(results) >= max_results:
                    break
        return results
    except Exception as e:
        print(f"Bing OSINT error: {e}")
        return []

def parse_bing_result(item: dict, target_location: str = "Chennai"):
    raw_title = item.get("title_raw", "")
    snippet = item.get("snippet", "")
    url = item.get("url", "")

    cleaned_title = re.sub(r'\s*\|\s*LinkedIn.*$', '', raw_title, flags=re.IGNORECASE)
    parts = [p.strip() for p in cleaned_title.split('-') if p.strip()]

    name = parts[0] if parts else "LinkedIn Executive"
    title = parts[1] if len(parts) > 1 else "Corporate Professional"
    org = parts[2] if len(parts) > 2 else "Enterprise"

    return {
        "name": name,
        "title": title,
        "organization": org,
        "email": "",
        "location": f"{target_location}, Tamil Nadu",
        "linkedin_url": url,
        "notes": f"Bing OSINT Match: {snippet[:250]}",
        "source": "bing_osint",
        "status": "discovered"
    }
