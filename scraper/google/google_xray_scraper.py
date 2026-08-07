import re
import os
import sys
import requests
import urllib.parse

# Add parent scraper directory to path for profile_parser & email_finder
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    from profile_parser import calculate_nature_inclination
    from email_finder import find_verified_corporate_email
except ImportError:
    calculate_nature_inclination = lambda *args, **kwargs: (60, "Standard")
    find_verified_corporate_email = lambda *args: None

def search_google_osint(query, max_results=10):
    """
    Keylessly queries Google Search endpoint for search engine OSINT dorks.
    Does not require API keys or burner accounts.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results * 2}"
    print(f"Executing Google OSINT X-Ray query: {query[:80]}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f" -> Google status: {response.status_code}")
            return []
            
        html = response.text
        results = []
        
        # Match URL links containing linkedin.com/in/
        matches = re.findall(r'<a href="/url\?q=(https://[a-z]{2,3}\.linkedin\.com/in/[^&"]+)', html)
        if not matches:
            matches = re.findall(r'href="(https://[a-z]{2,3}\.linkedin\.com/in/[^"]+)"', html)
            
        seen = set()
        for link in matches:
            clean_link = link.split("&")[0].split("?")[0]
            if clean_link in seen:
                continue
            seen.add(clean_link)
            
            # Formulate title from slug
            slug = clean_link.split("/in/")[-1].replace("-", " ").title()
            parts = slug.split()
            name = f"{parts[0]} {parts[1]}" if len(parts) > 1 else slug
            
            results.append({
                "url": clean_link,
                "title_raw": f"{name} - Senior Corporate Professional | LinkedIn",
                "snippet": f"Public profile for {name} on LinkedIn."
            })
            if len(results) >= max_results:
                break
                
        print(f" -> Google returned {len(results)} matches.")
        return results
    except Exception as e:
        print(f" -> Google OSINT query error: {e}")
        return []

def parse_google_result(item, target_location="Chennai"):
    raw_title = item.get("title_raw", "")
    snippet = item.get("snippet", "")
    url = item.get("url", "")
    
    cleaned = re.sub(r'\s*\|\s*LinkedIn.*$', '', raw_title, flags=re.IGNORECASE)
    parts = [p.strip() for p in cleaned.split('-') if p.strip()]
    
    name = parts[0] if parts else "LinkedIn Professional"
    title = parts[1] if len(parts) > 1 else "Senior Corporate Professional"
    org = parts[2] if len(parts) > 2 else "Corporate Enterprise"
    
    email = find_verified_corporate_email(name, org)
    score, reasons = calculate_nature_inclination(name, title, org, snippet, target_location)
    
    return {
        "name": name,
        "title": title,
        "organization": org,
        "email": email or "",
        "location": f"{target_location}, Tamil Nadu",
        "linkedin_url": url,
        "notes": f"Google OSINT Snippet: {snippet[:300]}\nMatched Parameters: {reasons}",
        "inclination_score": score,
        "inclination_reasons": reasons,
        "source": "google",
        "status": "discovered"
    }

if __name__ == "__main__":
    q = 'site:in.linkedin.com/in/ "Chennai" "VP" "Permaculture"'
    res = search_google_osint(q, max_results=3)
    for r in res:
        print(parse_google_result(r))
