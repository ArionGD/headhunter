import re
import json
import time
import requests
import urllib.parse
from profile_parser import calculate_nature_inclination
from email_finder import find_verified_corporate_email

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

def search_duckduckgo_osint(query, max_results=5, offset=0):
    """
    Keylessly queries DuckDuckGo via duckduckgo_search DDGS Python library.
    Supports pagination offsets for background batch streaming.
    """
    print(f"Executing DDGS OSINT X-Ray query (offset={offset}, limit={max_results}): {query[:80]}...")
    results = []
    total_needed = max_results + offset
    
    # 1. Try official DDGS library first
    try:
        with DDGS() as ddgs:
            raw_res = list(ddgs.text(query, max_results=total_needed * 2))
            for item in raw_res:
                href = item.get("href", "")
                if "linkedin.com/in/" in href:
                    results.append({
                        "url": href,
                        "title_raw": item.get("title", ""),
                        "snippet": item.get("body", "")
                    })
                    if len(results) >= total_needed:
                        break
        if len(results) > offset:
            paged_results = results[offset:offset + max_results]
            print(f" -> DDGS returned {len(paged_results)} profile matches for batch.")
            return paged_results
    except Exception as exc:
        print(f" -> DDGS library notice: {exc}. Attempting direct HTTP fallback...")

    # 2. Fallback to direct HTML scraper
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 HeadHunt/2.0"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            html = response.text
            matches = re.findall(r'<a class="result__url" href="([^"]+)"[^>]*>\s*([^<]+)', html)
            snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
            
            for idx, (link, link_text) in enumerate(matches):
                if "linkedin.com/in/" in link:
                    if "uddg=" in link:
                        parsed_uddg = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                        if "uddg" in parsed_uddg:
                            link = parsed_uddg["uddg"][0]
                            
                    snippet_text = re.sub(r'<[^>]+>', '', snippets[idx]).strip() if idx < len(snippets) else ""
                    results.append({
                        "url": link,
                        "title_raw": link_text.strip(),
                        "snippet": snippet_text
                    })
                    if len(results) >= total_needed:
                        break
        return results[offset:offset + max_results]
    except Exception as e:
        print(f" -> OSINT Fallback Query error: {e}")
        return []

def parse_xray_result(item, target_location="Chennai"):
    """
    Parses a raw search engine result into a structured lead dict.
    e.g. title_raw: "Sanjay Krishnan - Vice President Operations - TCS | LinkedIn"
    """
    raw_title = item.get("title_raw", "")
    snippet = item.get("snippet", "")
    url = item.get("url", "")
    
    # Remove "| LinkedIn" suffix
    cleaned_title = re.sub(r'\s*\|\s*LinkedIn.*$', '', raw_title, flags=re.IGNORECASE)
    parts = [p.strip() for p in cleaned_title.split('-') if p.strip()]
    
    name = parts[0] if parts else "LinkedIn Professional"
    title = parts[1] if len(parts) > 1 else "Senior Corporate Professional"
    org = parts[2] if len(parts) > 2 else "Corporate Enterprise"
    
    # Clean name if contains extra text
    if " " not in name and len(parts) > 1:
        name = f"{name} {parts[1]}"
        title = parts[2] if len(parts) > 2 else "Corporate Professional"
        
    email = find_verified_corporate_email(name, org, snippet_text=snippet)
    score, reasons = calculate_nature_inclination(name, title, org, snippet, target_location)
    
    return {
        "name": name,
        "title": title,
        "organization": org,
        "email": email or "",
        "location": f"{target_location}, Tamil Nadu",
        "linkedin_url": url,
        "notes": f"OSINT Snippet: {snippet[:300]}\nMatched Parameters: {reasons}",
        "inclination_score": score,
        "inclination_reasons": reasons,
        "source": "xray_osint",
        "status": "discovered"
    }

if __name__ == "__main__":
    query = 'site:in.linkedin.com/in/ "Chennai" "VP" "Permaculture"'
    raw_items = search_duckduckgo_osint(query, max_results=3)
    for raw in raw_items:
        parsed = parse_xray_result(raw)
        print(f"Name: {parsed['name']} | Title: {parsed['title']} | Org: {parsed['organization']} | Score: {parsed['inclination_score']}%")
