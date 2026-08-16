import requests

def search_github_leaders(location: str = "Chennai", keyword: str = "", limit: int = 5):
    """
    Keyless GitHub API harvester fetching tech leads, software architects, and senior developers.
    """
    print(f"Executing GitHub Harvester for location={location}, keyword={keyword}...")
    headers = {
        "User-Agent": "HeadHuntOSINT/2.0",
        "Accept": "application/vnd.github.v3+json"
    }

    # Query GitHub Users API
    query_str = f"location:{location}"
    if keyword:
        query_str += f" {keyword}"

    url = f"https://api.github.com/search/users?q={requests.utils.quote(query_str)}&per_page={limit * 2}"
    prospects = []

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for user in items:
                username = user.get("login")
                user_detail_url = f"https://api.github.com/users/{username}"
                detail_resp = requests.get(user_detail_url, headers=headers, timeout=8)

                if detail_resp.status_code == 200:
                    d = detail_resp.json()
                    full_name = d.get("name") or username
                    company = d.get("company") or "Independent Tech Lead"
                    bio = d.get("bio") or "Senior Software Engineer / Tech Lead"
                    email = d.get("email") or f"{username}@users.noreply.github.com"
                    user_loc = d.get("location") or location
                    blog = d.get("blog") or d.get("html_url")

                    prospects.append({
                        "name": full_name,
                        "title": "Software Architect / Tech Lead",
                        "organization": company.lstrip("@"),
                        "email": email if email and not email.endswith("noreply.github.com") else "",
                        "location": user_loc,
                        "linkedin_url": blog if blog.startswith("http") else d.get("html_url"),
                        "notes": f"GitHub Developer Bio: {bio[:200]}\nPublic Repos: {d.get('public_repos', 0)} | Followers: {d.get('followers', 0)}",
                        "source": "github",
                        "status": "discovered"
                    })
                    if len(prospects) >= limit:
                        break
        return prospects
    except Exception as e:
        print(f"GitHub Harvester error: {e}")
        return []
