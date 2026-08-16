import requests
import time

def search_reddit_harvester(subreddit: str = "Chennai", keyword: str = "permaculture", limit: int = 5):
    """
    Keyless Reddit API miner searching regional subreddits for sustainability advocates.
    """
    print(f"Executing Reddit Harvester for r/{subreddit} with keyword={keyword}...")
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        "q": keyword,
        "restrict_sr": "on",
        "limit": limit,
        "sort": "relevance"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 HeadHunt/2.0"
    }

    prospects = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                pdata = post.get("data", {})
                author = pdata.get("author")
                if not author or author.lower() in ("automoderator", "[deleted]", "deleted"):
                    continue

                title = pdata.get("title", "")
                selftext = pdata.get("selftext", "")
                permalink = f"https://reddit.com{pdata.get('permalink')}"

                prospects.append({
                    "name": f"u/{author}",
                    "title": "Sustainability Community Advocate",
                    "organization": f"Reddit r/{subreddit}",
                    "email": "",
                    "location": f"{subreddit} Region, India",
                    "linkedin_url": permalink,
                    "notes": f"Reddit Thread Title: {title}\nExcerpt: {selftext[:250]}...",
                    "source": "reddit",
                    "status": "discovered"
                })
                if len(prospects) >= limit:
                    break
        return prospects
    except Exception as e:
        print(f"Reddit Harvester error: {e}")
        return []
