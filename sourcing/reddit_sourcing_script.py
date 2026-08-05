import os
import json
import time
import requests
import argparse

def search_reddit_subreddit(subreddit, keyword, limit=25):
    """
    Searches a subreddit for a keyword using Reddit's public JSON search endpoint.
    Doesn't require API credentials, but uses custom User-Agent headers to avoid rate limits.
    """
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        "q": keyword,
        "restrict_sr": "on",
        "limit": limit,
        "sort": "relevance"
    }
    # Custom user-agent to prevent HTTP 429 Rate Limit responses
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 HeadHunt/1.0"
    }
    
    print(f"Searching r/{subreddit} for '{keyword}'...")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            print(f" -> Found {len(posts)} threads.")
            return posts
        elif response.status_code == 429:
            print(" -> Reddit returned HTTP 429 (Too Many Requests). Rate limit hit. Waiting to cool down...")
            return []
        else:
            print(f" -> Failed with HTTP status {response.status_code}")
            return []
    except Exception as e:
        print(f" -> Error during request: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Reddit public post miner for Chennai & Bangalore sustainability leads.")
    parser.add_argument("--subreddits", default="Chennai,bangalore,TamilNadu", help="Subreddits to search (comma-separated)")
    parser.add_argument("--keywords", default="permaculture,organic farming,terrace garden,farmland,nursery", 
                        help="Keywords to search for (comma-separated)")
    parser.add_argument("--limit", type=int, default=25, help="Number of search threads per keyword query")
    parser.add_argument("--output", default="reddit_leads.json", help="Path to save the resulting leads JSON")
    
    args = parser.parse_args()
    
    subreddits = [s.strip() for s in args.subreddits.split(",") if s.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    
    extracted_leads = []
    seen_authors = set() # Avoid duplicates in this run
    
    for sub in subreddits:
        for keyword in keywords:
            posts = search_reddit_subreddit(sub, keyword, limit=args.limit)
            
            for post in posts:
                post_data = post.get("data", {})
                author = post_data.get("author")
                
                # Filter out system moderators and deleted accounts
                if not author or author.lower() in ("automoderator", "[deleted]", "deleted"):
                    continue
                    
                if author in seen_authors:
                    continue
                    
                seen_authors.add(author)
                
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                permalink = f"https://reddit.com{post_data.get('permalink')}"
                created_utc = post_data.get("created_utc")
                
                # Formulate notes with thread info
                notes = f"Reddit Post Title: {title}\nThread Link: {permalink}\n\nSelf-Text:\n{selftext[:400]}..."
                
                # Format to map Lead model schema
                lead = {
                    "name": f"u/{author}",
                    "title": "Community Contributor",
                    "organization": f"Reddit r/{sub}",
                    "location": f"{sub} Region, India",
                    "linkedin_url": permalink, # Save post link as reference url
                    "notes": notes,
                    "source": "reddit",
                    "status": "discovered"
                }
                extracted_leads.append(lead)
                
            # Rate limiting friendly pause
            time.sleep(2)
            
    # Save output
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(extracted_leads, f, indent=4, ensure_ascii=False)
        print(f"\nDone! Extracted {len(extracted_leads)} unique user leads. Saved to: {output_path}")
        print("To sync this to your hosted dashboard database, run:")
        print(f"python sync_leads.py {args.output}")
    except Exception as e:
        print(f"Error saving leads file: {e}")

if __name__ == "__main__":
    main()
